def safe_profile(request):
    """
    Adds 'user_profile' and 'user_provider' safely to templates without raising
    RelatedObjectDoesNotExist when the relations are missing.
    """
    if not request.user.is_authenticated:
        return {"user_profile": None, "user_provider": None}

    profile = getattr(request.user, "profile", None)

    provider = None
    try:
        provider = getattr(request.user, "provider", None)
    except Exception:
        provider = None

    return {"user_profile": profile, "user_provider": provider}
