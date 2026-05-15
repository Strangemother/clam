"""Shared Flask blueprint for the prompting sub-application."""

from flask import Blueprint


prompting_bp = Blueprint("prompting", __name__, url_prefix="/prompting")


__all__ = ["prompting_bp"]
