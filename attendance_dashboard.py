import sys
import os
import pandas as pd
import subprocess
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTableWidget, QTableWidgetItem, QPushButton, QLabel, 
                             QMessageBox, QHeaderView)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QIcon

ATTENDANCE_FILE = "attendance.csv"
SCANNER_SCRIPT = "attendance_system_pro.py"

class AttendanceDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Attendance Dashboard")
        self.resize(900, 600)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
            }
            QTableWidget {
                background-color: #2d2d2d;
                gridline-color: #444;
                border: 1px solid #444;
                font-size: 14px;
            }
            QTableWidget::item {
                padding: 10px;
            }
            QHeaderView::section {
                background-color: #333;
                padding: 8px;
                border: 1px solid #444;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        
        self.setup_ui()
        
        # Auto-refresh timer (every 2 seconds)
        self.timer = QTimer()
        self.timer.timeout.connect(self.load_data)
        self.timer.start(2000)
        
        self.load_data()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("📋 Live Attendance Monitor")
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #00e5ff;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.status_label = QLabel("Status: Active")
        self.status_label.setStyleSheet("color: #77ff77; font-size: 14px;")
        controls_layout.addWidget(self.status_label)
        
        controls_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Refresh Data")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setStyleSheet(self.btn_style("#007bff"))
        self.refresh_btn.clicked.connect(self.load_data)
        controls_layout.addWidget(self.refresh_btn)
        
        self.start_btn = QPushButton("📷 Launch Scanner")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setStyleSheet(self.btn_style("#28a745"))
        self.start_btn.clicked.connect(self.start_scanner)
        controls_layout.addWidget(self.start_btn)
        
        main_layout.addLayout(controls_layout)
        
        # Data Table
        self.table = QTableWidget()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        main_layout.addWidget(self.table)
        
        # Footer
        footer = QLabel("System Ready • Auto-refreshing every 2s")
        footer.setStyleSheet("color: #888; font-size: 12px;")
        footer.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(footer)
        
        self.setLayout(main_layout)

    def btn_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
            QPushButton:pressed {{
                background-color: {color}aa;
            }}
        """

    def load_data(self):
        if not os.path.exists(ATTENDANCE_FILE):
             # Create empty if not exists
             pd.DataFrame(columns=["Name", "Date", "Time"]).to_csv(ATTENDANCE_FILE, index=False)
        
        try:
            df = pd.read_csv(ATTENDANCE_FILE)
            
            # Sort: Assuming entries are appended, reverse to show latest first
            if not df.empty:
                df = df.iloc[::-1]

            self.table.setRowCount(len(df))
            cols = list(df.columns)
            self.table.setColumnCount(len(cols))
            self.table.setHorizontalHeaderLabels(cols)
            
            for i, row in enumerate(df.values):
                for j, val in enumerate(row):
                    item = QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(i, j, item)
            
            self.status_label.setText(f"Status: Updated at {pd.Timestamp.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.status_label.setText("Status: Error reading file")
            print(f"Error: {e}")

    def start_scanner(self):
        try:
            # Check if script exists
            if not os.path.exists(SCANNER_SCRIPT):
                QMessageBox.warning(self, "File Not Found", f"Could not find {SCANNER_SCRIPT}")
                return

            # Launch in separate process
            subprocess.Popen([sys.executable, SCANNER_SCRIPT])
            self.status_label.setText("Status: Scanner Launched")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start scanner: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Optional: Set app icon if you had one, jumping to standard window for now
    
    win = AttendanceDashboard()
    win.show()
    sys.exit(app.exec_())
