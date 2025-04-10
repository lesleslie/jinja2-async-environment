from jinja2.sandbox import SandboxedEnvironment
from .environment import AsyncEnvironment


class AsyncSandBoxedEnvironment(AsyncEnvironment, SandboxedEnvironment):
    """A sandboxed environment that supports async operations.

    This environment combines the safety features of SandboxedEnvironment
    with the async capabilities of AsyncEnvironment.
    """

    pass
