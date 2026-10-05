# -*- coding: utf-8 -*-
"""
Lead Agent - Customer discovery and analysis
"""

from typing import List, Dict, Any, Optional

from services.base_service import BaseService
from services.lead_service import LeadService
from services.product_service import ProductService
from ai.ai_manager import AIManager
from repositories.lead_repository import LeadRepository
from integrations.reddit import RedditIntegration
from integrations.github import GitHubIntegration
from integrations.mock.reddit_mock import MockRedditIntegration
from integrations.mock.github_mock import MockGitHubIntegration
from utils.exceptions import APIError


class LeadAgent(BaseService):
    """
    Lead Agent responsible for:
    - Customer finding
    - Customer analysis
    """

    #: Search phrases used when discovering leads
    DEFAULT_QUERIES = [
        "looking for a tool",
        "need software to",
        "any recommendation for automation",
        "is there an app that",
        "how can I automate",
    ]

    def __init__(self, use_mock: Optional[bool] = None):
        """
        use_mock:
            None  -> auto: real integrations when configured, mocks otherwise
            True  -> force mocks (unit tests / offline demo)
            False -> force real integrations; errors are reported, not hidden
        """
        super().__init__()
        self.agent_type = "lead"
        self.lead_service = LeadService()
        self.product_service = ProductService()
        self.ai_manager = AIManager()
        self.lead_repo = LeadRepository()
        self.use_mock = use_mock
        #: Errors from the most recent find_leads() run, keyed by platform
        self.last_errors: Dict[str, str] = {}

    def using_mock(self, platform: str) -> bool:
        """Decide whether this platform runs against the mock or the real API"""
        if self.use_mock is not None:
            return self.use_mock
        integration = (
            RedditIntegration() if platform == "reddit" else GitHubIntegration()
        )
        return not integration.is_configured()

    def _get_integration(self, platform: str):
        """Return the integration client for a platform"""
        if platform == "reddit":
            return MockRedditIntegration() if self.using_mock("reddit") \
                else RedditIntegration()
        if platform == "github":
            return MockGitHubIntegration() if self.using_mock("github") \
                else GitHubIntegration()
        raise APIError(f"LeadAgent: unsupported platform '{platform}'")

    def find_leads(self, platform: str = None,
                   queries: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Find potential leads from the configured platforms.

        Real API failures are logged and recorded in self.last_errors; they are
        never turned into fake leads or silent empty results.
        """
        self.logger.info(f"Finding leads on {platform or 'all platforms'}")
        found_leads: List[Dict[str, Any]] = []
        platforms = [platform] if platform else ['reddit', 'github']
        queries = queries or self.DEFAULT_QUERIES
        self.last_errors = {}

        for p in platforms:
            try:
                client = self._get_integration(p)
                if p == 'reddit':
                    posts = client.search_relevant_posts(
                        queries, limit_per_query=15
                    )
                    for post in posts:
                        lead_data = self._normalize_reddit_post(post)
                        saved = self._save_lead_if_new(lead_data)
                        if saved:
                            found_leads.append(saved)
                elif p == 'github':
                    issues = client.search_feature_requests(
                        queries[0], limit=15
                    )
                    for issue in issues:
                        lead_data = self._normalize_github_issue(issue)
                        saved = self._save_lead_if_new(lead_data)
                        if saved:
                            found_leads.append(saved)
                self.logger.info(
                    f"{p}: {len(found_leads)} new lead(s) collected "
                    f"(source={'mock' if self.using_mock(p) else 'real API'})"
                )
            except Exception as e:
                self.last_errors[p] = str(e)
                self.logger.error(f"Error finding leads on {p}: {e}")

        if self.last_errors:
            self.logger.warning(
                f"Lead discovery finished with errors: {self.last_errors}"
            )
        return found_leads

    @staticmethod
    def _normalize_reddit_post(post: Dict) -> Dict:
        """
        Normalize a Reddit post.

        Handles the real Reddit API shape (author/selftext/permalink) and the
        mock shape (username/body/source_url).
        """
        username = post.get('author') or post.get('username')
        permalink = post.get('permalink') or ''
        if permalink and not permalink.startswith('http'):
            source_url = f"https://www.reddit.com{permalink}"
        else:
            source_url = post.get('source_url') or permalink
        return {
            'platform': 'reddit',
            'username': username,
            'platform_id': post.get('id') or post.get('platform_id'),
            'source_url': source_url,
            'profile_url': f"https://reddit.com/u/{username}" if username else None,
            'need': post.get('title'),
            'need_description': post.get('selftext') or post.get('body') or None,
            'external_ref': source_url,
        }

    @staticmethod
    def _normalize_github_issue(issue: Dict) -> Dict:
        """
        Normalize a GitHub issue.

        Handles the real GitHub API shape (user.login/body/html_url) and the
        mock shape (username/body/source_url).
        """
        user = issue.get('user') or {}
        username = user.get('login') if isinstance(user, dict) else None
        username = username or issue.get('username')
        source_url = issue.get('html_url') or issue.get('source_url')
        return {
            'platform': 'github',
            'username': username,
            'platform_id': issue.get('number') or issue.get('platform_id'),
            'source_url': source_url,
            'profile_url': f"https://github.com/{username}" if username else None,
            'need': issue.get('title'),
            'need_description': issue.get('body') or None,
            'external_ref': source_url,
        }

    def _save_lead_if_new(self, lead_data: Dict) -> Optional[Dict]:
        """
        Save a lead if it is not a duplicate.

        Duplicate detection order: source_url -> platform+platform_id ->
        platform+username. Checking the source URL first matters because the
        same user can post several needs, and each post is its own lead.
        """
        try:
            platform = lead_data.get('platform')
            source_url = lead_data.get('source_url')
            platform_id = lead_data.get('platform_id')
            username = lead_data.get('username')

            if not platform:
                self.logger.warning("Skipping lead without a platform")
                return None

            with self.db.session_scope() as session:
                duplicate = None
                if source_url:
                    duplicate = self.lead_repo.get_by_source_url(session, source_url)
                if duplicate is None and platform_id:
                    duplicate = self.lead_repo.get_by_platform_and_id(
                        session, platform, str(platform_id)
                    )
                # Username is only a last resort: the same person can raise
                # several distinct needs from one account.
                if duplicate is None and username and not (source_url or platform_id):
                    duplicate = self.lead_repo.get_by_username_and_platform(
                        session, username, platform
                    )
                if duplicate is not None:
                    self.logger.info(
                        f"Duplicate lead skipped: {platform}:"
                        f"{source_url or username or platform_id}"
                    )
                    return None

            # external_ref is not a model column
            clean = {k: v for k, v in lead_data.items() if k != 'external_ref'}
            saved = self.lead_service.create_lead(**clean)
            return saved
        except Exception as e:
            self.logger.error(f"Error saving lead: {e}")
            return None

    def analyze_lead(self, lead_id: int) -> Dict[str, Any]:
        """
        Analyze a lead using AI and store the result.

        Raises APIError when the AI call fails or the lead does not exist -
        an empty dict is never returned to hide a failure.
        """
        self.logger.info(f"Analyzing lead {lead_id}")
        lead = self.lead_service.get_lead(lead_id)
        if not lead:
            raise APIError(f"LeadAgent: lead {lead_id} not found")

        products = self.product_service.get_active_products()
        product_brief = [
            {
                'id': p.get('id'),
                'name': p.get('name'),
                'description': (p.get('description') or '')[:200],
                'price': str(p.get('price')),
            }
            for p in products[:5]
        ]

        prompt = (
            "Analyze this lead for sales potential. Reply with ONLY valid JSON.\n\n"
            f"Lead: {lead.get('need')} | "
            f"{lead.get('need_description')} | platform={lead.get('platform')}\n"
            f"Products: {product_brief}\n\n"
            'Return JSON with keys: need (string), need_description (string), '
            'product_match (product id from the list or null), '
            'buying_intent (low|medium|high), lead_quality (Low|Medium|High)'
        )

        # strict=True -> raises instead of returning a fake empty result
        result = self.ai_manager.generate_structured_response(prompt)

        product_id = self._validate_product_match(result.get('product_match'), products)
        quality = str(result.get('lead_quality') or 'Medium')
        if quality.lower() not in ('low', 'medium', 'high'):
            quality = 'Medium'

        # need is a 255 char column
        need = (result.get('need') or lead.get('need') or '')[:255]

        self.lead_service.update_lead(
            lead_id,
            need=need,
            need_description=result.get('need_description')
            or lead.get('need_description'),
            suggested_product_id=product_id,
            lead_quality=quality,
            status='analyzed',
        )
        self.logger.info(
            f"Lead {lead_id} analyzed: quality={quality} product_match={product_id}"
        )
        return result

    @staticmethod
    def _validate_product_match(value: Any, products: List[Dict]) -> Optional[int]:
        """
        Only accept a product id that actually exists in our catalogue.

        The AI may hallucinate an id or return a name; both are rejected.
        """
        if value is None:
            return None
        valid_ids = {p.get('id') for p in products if p.get('id') is not None}
        try:
            product_id = int(value)
        except (TypeError, ValueError):
            return None
        return product_id if product_id in valid_ids else None
