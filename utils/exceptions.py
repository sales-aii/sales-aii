# -*- coding: utf-8 -*-
"""
Centralized exception handling for Sales.aii
"""


class SalesAiiException(Exception):
    """Base exception for Sales.aii"""
    pass


class DatabaseError(SalesAiiException):
    """Database related errors"""
    pass


class ConfigError(SalesAiiException):
    """Configuration related errors"""
    pass


class APIError(SalesAiiException):
    """API integration errors"""
    pass


class AgentError(SalesAiiException):
    """Agent related errors"""
    pass


class ValidationError(SalesAiiException):
    """Validation errors"""
    pass
