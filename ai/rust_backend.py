"""Optional native CPU engine. Import only when Rust is explicitly selected."""

def native_module():
    try:
        import bilspill_ai_native
    except ImportError as error:
        raise RuntimeError(
            'Rust backend is not installed in this Python environment. '
            'Run: python -m pip install ./rust/ai_native (requires Cargo).'
        ) from error
    return bilspill_ai_native
