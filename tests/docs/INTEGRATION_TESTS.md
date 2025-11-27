# Integration Tests Plan

## Loader Combination Tests

```python
import pytest
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import (
    AsyncDictLoader,
    AsyncFileSystemLoader,
    AsyncFunctionLoader,
    AsyncChoiceLoader,
)


class TestLoaderCombinations:
    """Test various combinations of loaders with ChoiceLoader."""

    def test_filesystem_dict_choice_loader(self, tmp_path):
        """Test ChoiceLoader with FileSystemLoader and DictLoader."""
        # Create filesystem templates
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "fs_template.html").write_text("<h1>FS Template</h1>")

        # Dict templates
        dict_templates = {"dict_template.html": "<h2>Dict Template</h2>"}

        # Create choice loader
        fs_loader = AsyncFileSystemLoader(templates_dir)
        dict_loader = AsyncDictLoader(dict_templates)
        choice_loader = AsyncChoiceLoader([fs_loader, dict_loader])

        env = AsyncEnvironment(loader=choice_loader)

        # Test filesystem template
        template1 = asyncio.run(env.get_template_async("fs_template.html"))
        result1 = asyncio.run(template1.render_async())
        assert "FS Template" in result1

        # Test dict template
        template2 = asyncio.run(env.get_template_async("dict_template.html"))
        result2 = asyncio.run(template2.render_async())
        assert "Dict Template" in result2

    def test_nested_choice_loaders(self, tmp_path):
        """Test nested ChoiceLoader scenarios."""
        # Create multiple template sets
        templates_dir1 = tmp_path / "templates1"
        templates_dir1.mkdir()
        (templates_dir1 / "template1.html").write_text("<h1>Template 1</h1>")

        templates_dir2 = tmp_path / "templates2"
        templates_dir2.mkdir()
        (templates_dir2 / "template2.html").write_text("<h2>Template 2</h2>")

        dict_templates = {"template3.html": "<p>Template 3</p>"}

        # Create nested choice loaders
        fs_loader1 = AsyncFileSystemLoader(templates_dir1)
        fs_loader2 = AsyncFileSystemLoader(templates_dir2)
        dict_loader = AsyncDictLoader(dict_templates)

        # First level choice loader
        choice1 = AsyncChoiceLoader([fs_loader1, fs_loader2])
        # Second level choice loader
        choice2 = AsyncChoiceLoader([choice1, dict_loader])

        env = AsyncEnvironment(loader=choice2)

        # Test all templates
        template1 = asyncio.run(env.get_template_async("template1.html"))
        result1 = asyncio.run(template1.render_async())
        assert "Template 1" in result1

        template2 = asyncio.run(env.get_template_async("template2.html"))
        result2 = asyncio.run(template2.render_async())
        assert "Template 2" in result2

        template3 = asyncio.run(env.get_template_async("template3.html"))
        result3 = asyncio.run(template3.render_async())
        assert "Template 3" in result3

    def test_function_loader_with_fallback(self):
        """Test FunctionLoader with DictLoader fallback."""

        def custom_load_func(name):
            if name == "custom.html":
                return "<div>Custom Template</div>"
            return None  # Not found

        dict_templates = {"fallback.html": "<span>Fallback Template</span>"}

        func_loader = AsyncFunctionLoader(custom_load_func)
        dict_loader = AsyncDictLoader(dict_templates)
        choice_loader = AsyncChoiceLoader([func_loader, dict_loader])

        env = AsyncEnvironment(loader=choice_loader)

        # Test custom function template
        template1 = asyncio.run(env.get_template_async("custom.html"))
        result1 = asyncio.run(template1.render_async())
        assert "Custom Template" in result1

        # Test fallback template
        template2 = asyncio.run(env.get_template_async("fallback.html"))
        result2 = asyncio.run(template2.render_async())
        assert "Fallback Template" in result2
```

## Complex Template Scenario Tests

```python
import pytest
from jinja2_async_environment.environment import AsyncEnvironment
from jinja2_async_environment.loaders import AsyncDictLoader


class TestComplexTemplateScenarios:
    """Test complex template scenarios including inheritance, inclusion, and macros."""

    @pytest.fixture
    def complex_templates(self):
        return {
            # Base template with blocks
            "base.html": """
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Default Title{% endblock %}</title>
</head>
<body>
    <header>
        {% block header %}
        <h1>Default Header</h1>
        {% endblock %}
    </header>
    <main>
        {% block content %}{% endblock %}
    </main>
    <footer>
        {% block footer %}
        <p>Default Footer</p>
        {% endblock %}
    </footer>
</body>
</html>
            """,
            # Child template extending base
            "child.html": """
{% extends "base.html" %}
{% block title %}Child Page{% endblock %}
{% block header %}
<h1>Child Header</h1>
{% endblock %}
{% block content %}
<h2>Child Content</h2>
<p>{{ message }}</p>
{% endblock %}
            """,
            # Template with includes
            "include_target.html": "<p>Included Content: {{ included_var }}</p>",
            "include_template.html": """
<div>
    <h1>Main Content</h1>
    {% include "include_target.html" %}
</div>
            """,
            # Template with macros
            "macro_definitions.html": """
{% macro render_user(name, age, city="Unknown") -%}
<div class="user">
    <h3>{{ name }}</h3>
    <p>Age: {{ age }}</p>
    <p>City: {{ city }}</p>
</div>
{%- endmacro %}
            """,
            "macro_usage.html": """
{% from "macro_definitions.html" import render_user %}
<h1>User Directory</h1>
{{ render_user("Alice", 30, "New York") }}
{{ render_user("Bob", 25) }}
            """,
            # Template with complex filters
            "filter_template.html": """
<ul>
{% for item in items | sort(attribute="name") %}
    <li>{{ item.name | upper }}: {{ item.value | float | round(2) }}</li>
{% endfor %}
</ul>
            """,
        }

    def test_template_inheritance_chain(self, complex_templates):
        """Test complex template inheritance chains."""
        env = AsyncEnvironment(
            loader=AsyncDictLoader(complex_templates), enable_async=True
        )

        template = asyncio.run(env.get_template_async("child.html"))
        result = asyncio.run(template.render_async(message="Hello from child!"))

        assert "Child Page" in result
        assert "Child Header" in result
        assert "Hello from child!" in result
        assert "Default Footer" in result  # From base template

    def test_template_inclusion(self, complex_templates):
        """Test template inclusion functionality."""
        env = AsyncEnvironment(
            loader=AsyncDictLoader(complex_templates), enable_async=True
        )

        template = asyncio.run(env.get_template_async("include_template.html"))
        result = asyncio.run(template.render_async(included_var="Test Value"))

        assert "Main Content" in result
        assert "Included Content: Test Value" in result

    def test_macro_functionality(self, complex_templates):
        """Test macro definition and usage."""
        env = AsyncEnvironment(
            loader=AsyncDictLoader(complex_templates), enable_async=True
        )

        template = asyncio.run(env.get_template_async("macro_usage.html"))
        result = asyncio.run(template.render_async())

        assert "User Directory" in result
        assert "Alice" in result
        assert "Age: 30" in result
        assert "City: New York" in result
        assert "Bob" in result
        assert "Age: 25" in result
        assert "City: Unknown" in result

    def test_complex_filters(self, complex_templates):
        """Test complex filter chains."""
        env = AsyncEnvironment(
            loader=AsyncDictLoader(complex_templates), enable_async=True
        )

        context = {
            "items": [
                {"name": "zebra", "value": "3.14159"},
                {"name": "apple", "value": "2.71828"},
                {"name": "banana", "value": "1.41421"},
            ]
        }

        template = asyncio.run(env.get_template_async("filter_template.html"))
        result = asyncio.run(template.render_async(**context))

        # Check that items are sorted by name (apple, banana, zebra)
        # and values are processed with float and round filters
        assert "APPLE" in result
        assert "BANANA" in result
        assert "ZEBRA" in result
        assert "3.14" in result
        assert "2.72" in result
        assert "1.41" in result
```

## Real-world Usage Pattern Tests

```python
import pytest
from jinja2_async_environment.environment import (
    AsyncEnvironment,
    AsyncSandboxedEnvironment,
)
from jinja2_async_environment.loaders import AsyncDictLoader


class TestRealWorldUsagePatterns:
    """Test real-world usage patterns for web applications."""

    @pytest.fixture
    def web_templates(self):
        return {
            # Base layout for web application
            "layout.html": """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}My App{% endblock %}</title>
    <link rel="stylesheet" href="/static/style.css">
    {% block extra_head %}{% endblock %}
</head>
<body>
    <nav>
        <ul>
            <li><a href="/">Home</a></li>
            <li><a href="/users">Users</a></li>
            <li><a href="/about">About</a></li>
        </ul>
    </nav>

    <main>
        {% block content %}{% endblock %}
    </main>

    <footer>
        <p>&copy; 2023 My App. All rights reserved.</p>
    </footer>

    <script src="/static/script.js"></script>
    {% block extra_scripts %}{% endblock %}
</body>
</html>
            """,
            # Homepage template
            "index.html": """
{% extends "layout.html" %}
{% block title %}Home - My App{% endblock %}
{% block content %}
<h1>Welcome to My App</h1>
<p>{{ welcome_message }}</p>

{% if featured_users %}
<h2>Featured Users</h2>
<ul>
{% for user in featured_users %}
    <li>{{ user.name }} ({{ user.email }})</li>
{% endfor %}
</ul>
{% endif %}

<p>Current time: {{ current_time }}</p>
{% endblock %}
            """,
            # User list template
            "users/list.html": """
{% extends "layout.html" %}
{% block title %}Users - My App{% endblock %}
{% block content %}
<h1>User List</h1>

<form method="GET" action="/users">
    <input type="text" name="search" placeholder="Search users..." value="{{ search_query }}">
    <button type="submit">Search</button>
</form>

{% if users %}
<table>
    <thead>
        <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Join Date</th>
            <th>Status</th>
        </tr>
    </thead>
    <tbody>
    {% for user in users %}
        <tr>
            <td>{{ user.name }}</td>
            <td>{{ user.email }}</td>
            <td>{{ user.join_date.strftime("%Y-%m-%d") }}</td>
            <td class="{{ 'active' if user.is_active else 'inactive' }}">
                {{ 'Active' if user.is_active else 'Inactive' }}
            </td>
        </tr>
    {% endfor %}
    </tbody>
</table>

{% if pagination %}
<div class="pagination">
    {% if pagination.has_prev %}
        <a href="?page={{ pagination.prev_page }}">Previous</a>
    {% endif %}

    <span>Page {{ pagination.current_page }} of {{ pagination.total_pages }}</span>

    {% if pagination.has_next %}
        <a href="?page={{ pagination.next_page }}">Next</a>
    {% endif %}
</div>
{% endif %}

{% else %}
<p>No users found.</p>
{% endif %}
{% endblock %}
            """,
            # User profile template
            "users/profile.html": """
{% extends "layout.html" %}
{% block title %}{{ user.name }} - My App{% endblock %}
{% block content %}
<h1>User Profile: {{ user.name }}</h1>

<div class="user-info">
    <div class="field">
        <label>Email:</label>
        <span>{{ user.email }}</span>
    </div>
    <div class="field">
        <label>Join Date:</label>
        <span>{{ user.join_date.strftime("%B %d, %Y") }}</span>
    </div>
    <div class="field">
        <label>Status:</label>
        <span class="{{ 'active' if user.is_active else 'inactive' }}">
            {{ 'Active' if user.is_active else 'Inactive' }}
        </span>
    </div>
</div>

{% if user.bio %}
<div class="bio">
    <h2>Bio</h2>
    <p>{{ user.bio | safe }}</p>
</div>
{% endif %}

<h2>Recent Activity</h2>
{% if activities %}
<ul class="activity-list">
{% for activity in activities | sort(attribute="timestamp", reverse=true) %}
    <li class="activity">
        <span class="timestamp">{{ activity.timestamp.strftime("%Y-%m-%d %H:%M") }}</span>
        <span class="action">{{ activity.action }}</span>
    </li>
{% endfor %}
</ul>
{% else %}
<p>No recent activity.</p>
{% endif %}
{% endblock %}
            """,
        }

    def test_web_application_homepage(self, web_templates):
        """Test rendering a typical web application homepage."""
        env = AsyncEnvironment(loader=AsyncDictLoader(web_templates), enable_async=True)

        context = {
            "welcome_message": "Welcome to our amazing web application!",
            "featured_users": [
                {"name": "Alice Johnson", "email": "alice@example.com"},
                {"name": "Bob Smith", "email": "bob@example.com"},
            ],
            "current_time": "2023-12-01 10:30:00",
        }

        template = asyncio.run(env.get_template_async("index.html"))
        result = asyncio.run(template.render_async(**context))

        assert "Home - My App" in result
        assert "Welcome to our amazing web application!" in result
        assert "Alice Johnson" in result
        assert "bob@example.com" in result

    def test_web_application_user_list(self, web_templates):
        """Test rendering a user list page with pagination."""
        from datetime import datetime

        env = AsyncEnvironment(loader=AsyncDictLoader(web_templates), enable_async=True)

        context = {
            "users": [
                {
                    "name": "Alice Johnson",
                    "email": "alice@example.com",
                    "join_date": datetime(2023, 1, 15),
                    "is_active": True,
                },
                {
                    "name": "Bob Smith",
                    "email": "bob@example.com",
                    "join_date": datetime(2023, 3, 22),
                    "is_active": False,
                },
                {
                    "name": "Carol Williams",
                    "email": "carol@example.com",
                    "join_date": datetime(2023, 6, 10),
                    "is_active": True,
                },
            ],
            "pagination": {
                "current_page": 1,
                "total_pages": 3,
                "has_prev": False,
                "has_next": True,
                "next_page": 2,
            },
            "search_query": "",
        }

        template = asyncio.run(env.get_template_async("users/list.html"))
        result = asyncio.run(template.render_async(**context))

        assert "Users - My App" in result
        assert "Alice Johnson" in result
        assert "bob@example.com" in result
        assert "Active" in result
        assert "Inactive" in result
        assert "Page 1 of 3" in result

    def test_web_application_user_profile(self, web_templates):
        """Test rendering a user profile page with activity feed."""
        from datetime import datetime

        env = AsyncEnvironment(loader=AsyncDictLoader(web_templates), enable_async=True)

        context = {
            "user": {
                "name": "Alice Johnson",
                "email": "alice@example.com",
                "join_date": datetime(2023, 1, 15),
                "is_active": True,
                "bio": "<p>Software engineer passionate about open source.</p>",
            },
            "activities": [
                {
                    "timestamp": datetime(2023, 11, 30, 14, 30),
                    "action": "Updated profile picture",
                },
                {
                    "timestamp": datetime(2023, 11, 28, 9, 15),
                    "action": "Posted a new article",
                },
                {
                    "timestamp": datetime(2023, 11, 25, 16, 45),
                    "action": "Commented on forum thread",
                },
            ],
        }

        template = asyncio.run(env.get_template_async("users/profile.html"))
        result = asyncio.run(template.render_async(**context))

        assert "Alice Johnson - My App" in result
        assert "alice@example.com" in result
        assert "Software engineer passionate about open source" in result
        assert "Updated profile picture" in result
        assert "Posted a new article" in result
        assert "Commented on forum thread" in result

    def test_sandboxed_environment_security(self, web_templates):
        """Test security features of sandboxed environment."""
        env = AsyncSandboxedEnvironment(
            loader=AsyncDictLoader(web_templates), enable_async=True
        )

        # Test that dangerous operations are restricted
        unsafe_templates = {
            "unsafe.html": """
{% for x in [].append %}
{{ x }}
{% endfor %}
            """
        }

        env.loader = AsyncDictLoader(unsafe_templates)

        # This should raise a security exception
        with pytest.raises(
            Exception
        ):  # Specific exception depends on Jinja2's sandbox implementation
            template = asyncio.run(env.get_template_async("unsafe.html"))
            result = asyncio.run(template.render_async())
```
