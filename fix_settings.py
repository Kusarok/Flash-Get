import sys
from PyQt5.QtWidgets import QApplication
from settings_dialog import SettingsDialog, DARK_TERTIARY, TEXT_COLOR, DARK_SECONDARY, ACCENT_COLOR

app = QApplication(sys.argv)

# Crear una instancia de SettingsDialog
dialog = SettingsDialog()

# Modificar el tamaño
dialog.resize(600, 450)

# Modificar el estilo de las pestañas
new_style = f"""
    QTabBar::tab {{
        background-color: {DARK_TERTIARY};
        color: {TEXT_COLOR};
        padding: 10px 5px;
        min-width: 135px;
        max-width: 135px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-weight: bold;
        margin-right: 2px;
        margin-left: 2px;
    }}
    QTabBar::tab:selected {{
        background-color: {DARK_SECONDARY};
        border-bottom: 3px solid {ACCENT_COLOR};
    }}
"""

# Aplicar el estilo específico a las pestañas
dialog.tab_widget.setStyleSheet(new_style)

# Asegurarse de que las pestañas estén centradas
dialog.tab_widget.tabBar().setExpanding(True)

# Mostrar el diálogo
dialog.exec_()

sys.exit(app.exec_()) 