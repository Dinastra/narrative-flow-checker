import sys
import json
import traceback
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox,
    QPlainTextEdit,
)

from dialogue_validator import (
    load_json_file,
    validate_dialogue,
    attach_line_numbers_to_issues,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Narrative Flow Checker - Validador de Diálogos")
        self.resize(920, 620)

        # Arquivo padrão (se existir na mesma pasta)
        self.current_file = Path("dialogues.json")
        if not self.current_file.exists():
            self.current_file = None

        # ---------- Widgets ----------
        self.title_label = QLabel("Narrative Flow Checker")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")

        self.subtitle_label = QLabel("Validador de fluxo narrativo para jogos com diálogos ramificados")
        self.subtitle_label.setStyleSheet("color: #9aa0a6;")

        self.file_label = QLabel()
        self.file_label.setWordWrap(True)
        self.update_file_label()

        self.summary_label = QLabel("Nenhuma validação executada ainda.")
        self.summary_label.setStyleSheet("font-weight: bold;")

        self.open_button = QPushButton("Abrir JSON")
        self.open_button.clicked.connect(self.open_json_file)

        self.validate_button = QPushButton("Validar")
        self.validate_button.clicked.connect(self.validate_current_file)

        self.output_box = QPlainTextEdit()
        self.output_box.setReadOnly(True)
        self.output_box.setPlaceholderText("O relatório vai aparecer aqui...")

        if self.current_file:
            self.output_box.setPlainText(
                f"Arquivo padrão encontrado: {self.current_file}\nClique em 'Validar' para analisar."
            )

        # ---------- Layout ----------
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout()
        central.setLayout(main_layout)

        main_layout.addWidget(self.title_label)
        main_layout.addWidget(self.subtitle_label)
        main_layout.addSpacing(8)
        main_layout.addWidget(self.file_label)

        button_row = QHBoxLayout()
        button_row.addWidget(self.open_button)
        button_row.addWidget(self.validate_button)
        button_row.addStretch()
        main_layout.addLayout(button_row)

        main_layout.addWidget(self.summary_label)
        main_layout.addWidget(self.output_box)

    # ---------------------------------------------------------
    # UI helpers
    # ---------------------------------------------------------
    def update_file_label(self):
        if self.current_file:
            self.file_label.setText(f"📄 Arquivo atual: {self.current_file}")
        else:
            self.file_label.setText("📄 Nenhum arquivo selecionado.")

    def open_json_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar arquivo JSON",
            "",
            "Arquivos JSON (*.json)"
        )

        if file_path:
            self.current_file = Path(file_path)
            self.update_file_label()
            self.summary_label.setText("Arquivo selecionado. Clique em 'Validar'.")
            self.summary_label.setStyleSheet("font-weight: bold;")
            self.output_box.setPlainText(
                f"Arquivo selecionado: {self.current_file}\nClique em 'Validar' para analisar."
            )

    # ---------------------------------------------------------
    # Validação principal
    # ---------------------------------------------------------
    def validate_current_file(self):
        if not self.current_file:
            QMessageBox.warning(self, "Aviso", "Selecione um arquivo JSON primeiro.")
            return

        # 1) Ler JSON
        try:
            data = load_json_file(self.current_file)
        except FileNotFoundError:
            QMessageBox.critical(self, "Erro", f"Arquivo não encontrado:\n{self.current_file}")
            return
        except json.JSONDecodeError as e:
            # Aqui mostra linha e coluna do erro de sintaxe JSON
            QMessageBox.critical(
                self,
                "Erro de JSON",
                f"JSON inválido:\n{e.msg}\nLinha: {e.lineno}, Coluna: {e.colno}"
            )
            self.summary_label.setText("❌ JSON inválido.")
            self.summary_label.setStyleSheet("font-weight: bold; color: #b00020;")
            self.output_box.setPlainText(
                f"Erro de sintaxe JSON\n\nMensagem: {e.msg}\nLinha: {e.lineno}\nColuna: {e.colno}"
            )
            return
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro inesperado ao abrir o arquivo:\n{e}")
            self.summary_label.setText("❌ Erro ao abrir arquivo.")
            self.summary_label.setStyleSheet("font-weight: bold; color: #b00020;")
            self.output_box.setPlainText(traceback.format_exc())
            return

        # 2) Validar lógica narrativa
        try:
            issues = validate_dialogue(data)
            attach_line_numbers_to_issues(issues, str(self.current_file))
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro durante a validação:\n{e}")
            self.summary_label.setText("❌ Erro durante a validação.")
            self.summary_label.setStyleSheet("font-weight: bold; color: #b00020;")
            self.output_box.setPlainText(traceback.format_exc())
            return

        # 3) Atualiza resumo
        error_count = sum(1 for i in issues if i["level"] == "ERROR")
        warning_count = sum(1 for i in issues if i["level"] == "WARNING")
        info_count = sum(1 for i in issues if i["level"] == "INFO")

        if len(issues) == 0:
            self.summary_label.setText("✅ Nenhum problema encontrado.")
            self.summary_label.setStyleSheet("font-weight: bold; color: #0a7a2f;")
        else:
            self.summary_label.setText(
                f"Erros: {error_count} | Avisos: {warning_count} | Info: {info_count}"
            )

            if error_count > 0:
                self.summary_label.setStyleSheet("font-weight: bold; color: #b00020;")
            elif warning_count > 0:
                self.summary_label.setStyleSheet("font-weight: bold; color: #b36b00;")
            else:
                self.summary_label.setStyleSheet("font-weight: bold; color: #1565c0;")

        # 4) Mostra relatório
        report_text = self.format_report(issues)
        self.output_box.setPlainText(report_text)

    # ---------------------------------------------------------
    # Formatação do relatório exibido na interface
    # ---------------------------------------------------------
    def format_report(self, issues):
        if not issues:
            return "✅ Nenhum problema encontrado."

        order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
        issues_sorted = sorted(
            issues,
            key=lambda x: (order.get(x["level"], 99), x.get("code", ""), x.get("path", ""))
        )

        lines = []
        lines.append("=== RELATÓRIO DE VALIDAÇÃO ===")
        lines.append("")

        icons = {"ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}

        for issue in issues_sorted:
            icon = icons.get(issue["level"], "•")
            lines.append(f"{icon} [{issue['level']}] {issue['code']}")
            lines.append(f"   {issue['message']}")
            lines.append(f"   Path: {issue['path']}")
            if "line" in issue:
                lines.append(f"   Linha: {issue['line']}")
            lines.append("")

        return "\n".join(lines)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()