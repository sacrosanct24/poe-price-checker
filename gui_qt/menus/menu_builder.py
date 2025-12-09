"""
Declarative menu builder for PyQt6 applications.

Replaces repetitive imperative menu creation with a clean, data-driven approach.
Reduces ~350 lines of boilerplate to ~50 lines of configuration.
"""

from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, List, Union
import webbrowser
import logging

from PyQt6.QtWidgets import QMenuBar, QMenu, QWidget
from PyQt6.QtGui import QAction, QKeySequence

logger = logging.getLogger(__name__)


@dataclass
class MenuItem:
    """Configuration for a single menu item (action)."""
    text: str
    handler: Optional[Callable] = None
    shortcut: Optional[str] = None
    checkable: bool = False
    checked: bool = False
    enabled: bool = True
    url: Optional[str] = None  # For URL actions

    def __post_init__(self):
        # Auto-create URL handler if url is provided
        if self.url and not self.handler:
            self.handler = self._create_url_handler(self.url)

    def _create_url_handler(self, url: str) -> Callable:
        def open_url():
            webbrowser.open(url)
        return open_url


@dataclass
class MenuSection:
    """A group of menu items, optionally with a label."""
    items: List[Union[MenuItem, 'SubMenu']]
    label: Optional[str] = None  # Category label (disabled action)


@dataclass
class SubMenu:
    """Configuration for a submenu."""
    text: str
    items: List[Union[MenuItem, MenuSection, 'SubMenu']] = field(default_factory=list)


@dataclass
class MenuConfig:
    """Configuration for a top-level menu."""
    text: str
    items: List[Union[MenuItem, MenuSection, SubMenu]] = field(default_factory=list)


class MenuBuilder:
    """
    Builds Qt menus from declarative configuration.

    Usage:
        builder = MenuBuilder(parent_widget)
        config = [
            MenuConfig("&File", [
                MenuItem("&Open", handler=self.open_file, shortcut="Ctrl+O"),
                MenuSection([MenuItem("E&xit", handler=self.close)]),
            ])
        ]
        builder.build(menubar, config)
    """

    def __init__(self, parent: QWidget):
        """
        Initialize the menu builder.

        Args:
            parent: Parent widget for QAction instances
        """
        self.parent = parent
        self.actions: Dict[str, QAction] = {}  # Track actions by text for later access
        self.menus: Dict[str, QMenu] = {}  # Track menus by text

    def build(self, menubar: QMenuBar, config: List[MenuConfig]) -> None:
        """
        Build menus from configuration.

        Args:
            menubar: The QMenuBar to populate
            config: List of MenuConfig for top-level menus
        """
        for menu_config in config:
            menu = menubar.addMenu(menu_config.text)
            if menu:
                self.menus[menu_config.text] = menu
                self._populate_menu(menu, menu_config.items)

    def _populate_menu(
        self,
        menu: QMenu,
        items: List[Union[MenuItem, MenuSection, SubMenu]]
    ) -> None:
        """Recursively populate a menu with items."""
        for i, item in enumerate(items):
            if isinstance(item, MenuItem):
                self._add_action(menu, item)
            elif isinstance(item, MenuSection):
                if i > 0:  # Add separator before section (except first)
                    menu.addSeparator()
                if item.label:
                    label_action = QAction(f"[ {item.label} ]", self.parent)
                    label_action.setEnabled(False)
                    menu.addAction(label_action)
                for section_item in item.items:
                    if isinstance(section_item, MenuItem):
                        self._add_action(menu, section_item)
                    elif isinstance(section_item, SubMenu):
                        self._add_submenu(menu, section_item)
            elif isinstance(item, SubMenu):
                self._add_submenu(menu, item)

    def _add_action(self, menu: QMenu, item: MenuItem) -> QAction:
        """Create and add a QAction from MenuItem config."""
        action = QAction(item.text, self.parent)

        if item.shortcut:
            action.setShortcut(QKeySequence(item.shortcut))

        if item.checkable:
            action.setCheckable(True)
            action.setChecked(item.checked)

        action.setEnabled(item.enabled)

        if item.handler:
            action.triggered.connect(item.handler)

        menu.addAction(action)
        self.actions[item.text] = action
        return action

    def _add_submenu(self, parent_menu: QMenu, submenu: SubMenu) -> Optional[QMenu]:
        """Create and add a submenu."""
        menu = parent_menu.addMenu(submenu.text)
        if menu:
            self.menus[submenu.text] = menu
            self._populate_menu(menu, submenu.items)
        return menu

    def get_action(self, text: str) -> Optional[QAction]:
        """Get an action by its text."""
        return self.actions.get(text)

    def get_menu(self, text: str) -> Optional[QMenu]:
        """Get a menu by its text."""
        return self.menus.get(text)


# =============================================================================
# Resource Links Configuration
# =============================================================================

def create_poe1_resources() -> SubMenu:
    """Create PoE1 resources submenu configuration."""
    return SubMenu("Path of Exile &1", [
        SubMenu("Official", [
            MenuItem("Official Website", url="https://www.pathofexile.com/"),
            MenuItem("Official Trade", url="https://www.pathofexile.com/trade/search/Keepers"),
            MenuItem("Passive Skill Tree", url="https://www.pathofexile.com/passive-skill-tree"),
        ]),
        SubMenu("Wiki && Database", [
            MenuItem("Community Wiki", url="https://www.poewiki.net/wiki/Path_of_Exile_Wiki"),
            MenuItem("PoE DB", url="https://poedb.tw/us/"),
        ]),
        SubMenu("Build Planning", [
            MenuItem("Path of Building (Desktop)", url="https://pathofbuilding.community/"),
            MenuItem("Path of Building (Web)", url="https://pob.cool/"),
            MenuItem("PoE Planner", url="https://poeplanner.com/"),
            MenuItem("Path of Pathing (Atlas)", url="https://www.pathofpathing.com/"),
        ]),
        SubMenu("Build Guides", [
            MenuItem("Maxroll", url="https://maxroll.gg/poe"),
            MenuItem("Mobalytics", url="https://mobalytics.gg/poe"),
            MenuItem("PoE Builds", url="https://www.poebuilds.cc/"),
            MenuItem("Pohx (Righteous Fire)", url="https://pohx.net/"),
        ]),
        SubMenu("Economy && Trading", [
            MenuItem("Wealthy Exile", url="https://wealthyexile.com/"),
            MenuItem("Map Trade", url="https://poemap.trade/"),
            MenuItem("poe.how Economy Guide", url="https://poe.how/economy"),
        ]),
        SubMenu("Tools", [
            MenuItem("FilterBlade (Loot Filters)", url="https://www.filterblade.xyz/?game=Poe1"),
        ]),
        MenuSection([
            MenuItem("Reddit", url="https://www.reddit.com/r/pathofexile/"),
        ]),
    ])


def create_poe2_resources() -> SubMenu:
    """Create PoE2 resources submenu configuration."""
    return SubMenu("Path of Exile &2", [
        SubMenu("Official", [
            MenuItem("Official Website", url="https://pathofexile2.com/"),
            MenuItem("Official Trade", url="https://www.pathofexile.com/trade2/search/poe2/Rise%20of%20the%20Abyssal"),
        ]),
        SubMenu("Wiki && Database", [
            MenuItem("Community Wiki", url="https://www.poe2wiki.net/wiki/Path_of_Exile_2_Wiki"),
            MenuItem("PoE2 DB", url="https://poe2db.tw/"),
        ]),
        SubMenu("Build Planning", [
            MenuItem("Path of Building PoE2 (GitHub)", url="https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2"),
        ]),
        SubMenu("Build Guides", [
            MenuItem("Maxroll", url="https://maxroll.gg/poe2"),
            MenuItem("Mobalytics", url="https://mobalytics.gg/poe-2"),
        ]),
        SubMenu("Tools", [
            MenuItem("FilterBlade (Loot Filters)", url="https://www.filterblade.xyz/?game=Poe2"),
        ]),
        MenuSection([
            MenuItem("Reddit", url="https://www.reddit.com/r/PathOfExile2/"),
            MenuItem("Reddit Builds", url="https://www.reddit.com/r/pathofexile2builds/"),
        ]),
    ])


def create_resources_menu() -> List[Union[SubMenu, MenuSection, MenuItem]]:
    """Create the full Resources menu configuration."""
    return [
        create_poe1_resources(),
        create_poe2_resources(),
        MenuSection([
            MenuItem("poe.ninja (Economy)", url="https://poe.ninja/"),
            MenuItem("PoB Archives (Meta Builds)", url="https://pobarchives.com/"),
        ]),
    ]
