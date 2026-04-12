"""
Инициализация моделей БД
"""

from .Event import Event
from .Visitors import Visitor
from .Session import Session
from .User import User
from .Site import Site
from .Revision import Revision
from .Hypothesis import Hypothesis

__all__ = ['Event', 'Visitor', 'Session', 'User', 'Site', 'Revision', 'Hypothesis']
