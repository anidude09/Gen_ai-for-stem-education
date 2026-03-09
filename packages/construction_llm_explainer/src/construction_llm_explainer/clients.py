"""
clients.py

Lazy-loaded client initialization for OpenAI and Groq APIs safely.
"""

import os
import threading

_openai_client = None
_openai_lock = threading.Lock()
_openai_failed = False

_groq_client = None
_groq_lock = threading.Lock()
_groq_failed = False

def get_openai_client():
    global _openai_client, _openai_failed
    if _openai_failed:
        return None
    if _openai_client is not None:
        return _openai_client

    with _openai_lock:
        if _openai_client is not None:
            return _openai_client
        if _openai_failed:
            return None

        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                _openai_client = OpenAI(api_key=api_key)
                print("[construction_llm_explainer] OpenAI GPT-4o ready (primary)")
            else:
                print("[construction_llm_explainer] OPENAI_API_KEY not set")
                _openai_failed = True
        except ImportError:
            print("[construction_llm_explainer] openai package not installed")
            _openai_failed = True

    return _openai_client

def get_groq_client():
    global _groq_client, _groq_failed
    if _groq_failed:
        return None
    if _groq_client is not None:
        return _groq_client

    with _groq_lock:
        if _groq_client is not None:
            return _groq_client
        if _groq_failed:
            return None

        try:
            from groq import Groq
            api_key = os.getenv("GROQ_API_KEY")
            if api_key:
                _groq_client = Groq(api_key=api_key)
                print("[construction_llm_explainer] Groq client ready (fallback)")
            else:
                print("[construction_llm_explainer] GROQ_API_KEY not set")
                _groq_failed = True
        except ImportError:
            print("[construction_llm_explainer] groq package not installed")
            _groq_failed = True

    return _groq_client
