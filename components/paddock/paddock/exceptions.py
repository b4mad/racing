class RuntimeEnvironmentConfigurationIncompleteError(Exception):
    """
    This exception is raised when the runtime environment configuration is incomplete,
    i.e. one or more required environment variables are not set.
    """

    def __init__(self, *args):
        if not all(isinstance(arg, str) for arg in args):
            raise ValueError("All arguments must be strings.")
        self.messages = args
        super().__init__(*args)

    def __str__(self):
        return "\n".join(f"missing environment variable: {message}" for message in self.messages)
