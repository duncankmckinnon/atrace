from __future__ import annotations

import pytest

from atrace.platforms.base import Platform


class TestPlatformIsAbstract:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            Platform()


class TestSubclassMustImplement:
    def test_missing_install_and_uninstall(self):
        class Incomplete(Platform):
            name = "x"
            display_name = "X"

        with pytest.raises(TypeError):
            Incomplete()

    def test_missing_uninstall(self):
        class MissingUninstall(Platform):
            name = "x"
            display_name = "X"

            def install(self) -> None: ...

        with pytest.raises(TypeError):
            MissingUninstall()

    def test_missing_install(self):
        class MissingInstall(Platform):
            name = "x"
            display_name = "X"

            def uninstall(self) -> None: ...

        with pytest.raises(TypeError):
            MissingInstall()


class TestConcreteSubclass:
    def test_can_instantiate(self):
        class Concrete(Platform):
            name = "test"
            display_name = "Test Platform"

            def install(self) -> None: ...
            def uninstall(self) -> None: ...

        p = Concrete()
        assert p.name == "test"
        assert p.display_name == "Test Platform"

    def test_install_is_callable(self):
        class Concrete(Platform):
            name = "test"
            display_name = "Test Platform"

            def install(self) -> None: ...
            def uninstall(self) -> None: ...

        p = Concrete()
        assert p.install() is None

    def test_uninstall_is_callable(self):
        class Concrete(Platform):
            name = "test"
            display_name = "Test Platform"

            def install(self) -> None: ...
            def uninstall(self) -> None: ...

        p = Concrete()
        assert p.uninstall() is None
