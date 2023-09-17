class RuntimeEnvironmentConfigurationIncompleteError(Exception):
    """
    This exception is raised when the runtime environment configuration is incomplete,
    i.e. one or more required environment variables are not set.
    """

    def __init__(self, missing_env_vars):
        self.missing_env_vars = missing_env_vars
