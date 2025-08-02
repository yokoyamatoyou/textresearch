from tkinter import filedialog, messagebox
import customtkinter as ctk
import pandas as pd
import asyncio
import os
import threading
import queue

# プロジェクトのルートをsys.pathに追加
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis import analyze_dataframe, summarize_results
from reporting import generate_pdf_report, generate_wordcloud
from config import settings


def expand_key_topic_columns(
    df: pd.DataFrame, column: str = "analysis_key_topics"
) -> pd.DataFrame:
    """Convert list-based key topics column into separate columns."""
    if column not in df.columns:
        return df
    topics_expanded = (
        df[column].apply(lambda x: x if isinstance(x, list) else []).apply(pd.Series)
    )
    if topics_expanded.empty:
        return df.drop(columns=[column])
    topics_expanded.columns = [
        f"{column}_{i+1}" for i in range(len(topics_expanded.columns))
    ]
    return pd.concat([df.drop(columns=[column]), topics_expanded], axis=1)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("一括アンケート分析ツール")
        self.geometry("800x600")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.df = None
        self.df_analyzed = None
        self.summary_data = None
        self.wc_all_var = ctk.BooleanVar(value=True)
        self.wc_pos_var = ctk.BooleanVar(value=False)
        self.wc_neg_var = ctk.BooleanVar(value=False)
        self.analysis_queue = queue.Queue()
        self.check_queue()

        # --- メインフレーム ---
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # --- ファイル選択フレーム ---
        file_frame = ctk.CTkFrame(self.main_frame)
        file_frame.pack(pady=10, padx=10, fill="x")

        self.load_button = ctk.CTkButton(
            file_frame, text="Excelファイルを選択", command=self.load_file
        )
        self.load_button.pack(side="left", padx=10, pady=10)

        self.file_label = ctk.CTkLabel(file_frame, text="ファイルが選択されていません")
        self.file_label.pack(side="left", padx=10)

        # --- 列選択フレーム ---
        column_frame = ctk.CTkFrame(self.main_frame)
        column_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(column_frame, text="分析対象の列:").pack(side="left", padx=10)
        self.column_selector = ctk.CTkComboBox(
            column_frame, state="disabled", values=[]
        )
        self.column_selector.pack(side="left", padx=10)

        # --- 実行フレーム ---
        run_frame = ctk.CTkFrame(self.main_frame)
        run_frame.pack(pady=10, padx=10, fill="x")

        self.run_button = ctk.CTkButton(
            run_frame,
            text="分析実行",
            command=self.run_analysis_wrapper,
            state="disabled",
        )
        self.run_button.pack(pady=10)

        progress_frame = ctk.CTkFrame(run_frame)
        progress_frame.pack(pady=10, fill="x", expand=True)

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.set(0)
        self.progress_bar.pack(side="left", fill="x", expand=True)

        self.status_label = ctk.CTkLabel(progress_frame, text="準備完了")
        self.status_label.pack(side="right", padx=10)

        # --- ワードクラウド設定フレーム ---
        wc_frame = ctk.CTkFrame(self.main_frame)
        wc_frame.pack(pady=10, padx=10, fill="x")
        
        wc_options_frame = ctk.CTkFrame(wc_frame)
        wc_options_frame.pack(side="left", padx=10, pady=5)

        ctk.CTkLabel(wc_options_frame, text="ワードクラウド生成:").pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(wc_options_frame, text="全体", variable=self.wc_all_var).pack(side="left", padx=5)
        ctk.CTkCheckBox(wc_options_frame, text="ポジティブ", variable=self.wc_pos_var).pack(side="left", padx=5)
        ctk.CTkCheckBox(wc_options_frame, text="ネガティブ", variable=self.wc_neg_var).pack(side="left", padx=5)

        wc_exclude_frame = ctk.CTkFrame(wc_frame)
        wc_exclude_frame.pack(side="left", padx=10, pady=5, expand=True, fill="x")

        ctk.CTkLabel(wc_exclude_frame, text="除外ワード(カンマ区切り):").pack(side="left", padx=(0, 5))
        self.exclude_entry = ctk.CTkEntry(wc_exclude_frame, width=200)
        self.exclude_entry.pack(side="left", expand=True, fill="x")

        # --- 結果保存フレーム ---
        save_frame = ctk.CTkFrame(self.main_frame)
        save_frame.pack(pady=20, padx=10, fill="x")

        self.save_excel_button = ctk.CTkButton(
            save_frame,
            text="分析結果をExcelに保存",
            command=self.save_excel,
            state="disabled",
        )
        self.save_excel_button.pack(side="left", padx=10, pady=10, expand=True)

        self.save_pdf_button = ctk.CTkButton(
            save_frame,
            text="サマリーPDFを保存",
            command=self.save_pdf,
            state="disabled",
        )
        self.save_pdf_button.pack(side="left", padx=10, pady=10, expand=True)

        self.save_wordcloud_button = ctk.CTkButton(
            save_frame,
            text="ワードクラウドを保存",
            command=self.save_wordcloud,
            state="disabled",
        )
        self.save_wordcloud_button.pack(side="left", padx=10, pady=10, expand=True)

        # --- APIキーチェック ---
        if not settings.OPENAI_API_KEY:
            messagebox.showerror(
                "設定エラー", "OPENAI_API_KEYが環境変数に設定されていません。"
            )
            self.destroy()

    def load_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if not file_path:
            return

        try:
            self.df = pd.read_excel(file_path)
            self.file_label.configure(text=os.path.basename(file_path))
            self.column_selector.configure(
                values=self.df.columns.tolist(), state="normal"
            )
            self.column_selector.set(self.df.columns[0])
            self.run_button.configure(state="normal")
            self.reset_results()
        except Exception as e:
            messagebox.showerror(
                "読み込みエラー", f"ファイルの読み込みに失敗しました:\n{e}"
            )

    def reset_results(self):
        self.df_analyzed = None
        self.summary_data = None
        self.wordcloud_words = None
        self.save_excel_button.configure(state="disabled")
        self.save_pdf_button.configure(state="disabled")
        self.save_wordcloud_button.configure(state="disabled")
        self.progress_bar.set(0)
        self.status_label.configure(text="準備完了")

    def update_progress(self, value: float) -> None:
        """Update progress bar and corresponding status label."""

        self.progress_bar.set(min(value, 100) / 100)
        if value <= 0:
            status = "準備完了"
        elif value < 100:
            status = "分析中..."
        else:
            status = "完了"
        self.status_label.configure(text=status)
        self.update_idletasks()

    def check_queue(self):
        """Monitor background thread messages for GUI updates."""
        try:
            message = self.analysis_queue.get_nowait()
            if isinstance(message, float):
                self.update_progress(message)
            elif isinstance(message, dict) and "summary" in message:
                self.df_analyzed = message["df_analyzed"]
                self.summary_data = message["summary"]
                self.wordcloud_words = message["wordcloud_words"]
                messagebox.showinfo("完了", "分析が完了しました。結果を保存できます。")
                self.save_excel_button.configure(state="normal")
                self.save_pdf_button.configure(state="normal")
                self.save_wordcloud_button.configure(state="normal")
                self.run_button.configure(state="normal")
                self.load_button.configure(state="normal")
            elif isinstance(message, str) and message.startswith("ERROR"):
                messagebox.showerror("分析エラー", message)
                self.run_button.configure(state="normal")
                self.load_button.configure(state="normal")
        except queue.Empty:
            pass
        finally:
            self.after(100, self.check_queue)

    def run_analysis_wrapper(self):
        if self.df is None:
            messagebox.showerror("エラー", "ファイルが選択されていません。")
            return

        column = self.column_selector.get()
        if not column:
            messagebox.showerror("エラー", "分析対象の列を選択してください。")
            return

        self.reset_results()
        self.run_button.configure(state="disabled")
        self.load_button.configure(state="disabled")

        thread = threading.Thread(
            target=self.run_analysis_in_background, args=(column,)
        )
        thread.daemon = True
        thread.start()

    def run_analysis_in_background(self, column: str):
        """Execute analysis asynchronously inside a worker thread."""

        def progress_callback_for_thread(value: float):
            self.analysis_queue.put(value)

        async def run():
            try:
                df_analyzed = await analyze_dataframe(
                    self.df,
                    column,
                    progress_callback=progress_callback_for_thread,
                    max_concurrent_tasks=settings.MAX_CONCURRENT_TASKS,
                )
                progress_callback_for_thread(100.0)

                summary_data, wordcloud_words = await summarize_results(
                    df_analyzed,
                    column,
                )
                self.analysis_queue.put(
                    {
                        "df_analyzed": df_analyzed,
                        "summary": summary_data,
                        "wordcloud_words": wordcloud_words,
                    }
                )
            except Exception as e:
                self.analysis_queue.put(f"ERROR: 分析中にエラーが発生しました:\n{e}")

        asyncio.run(run())

    def save_excel(self):
        if self.df_analyzed is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")]
        )
        if path:
            try:
                df_to_save = expand_key_topic_columns(self.df_analyzed)
                df_to_save.to_excel(path, index=False)
                messagebox.showinfo("成功", f"分析結果を {path} に保存しました。")
            except Exception as e:
                messagebox.showerror(
                    "保存エラー", f"Excelファイルの保存に失敗しました:\n{e}"
                )

    def save_pdf(self):
        if self.summary_data is None:
            messagebox.showerror("エラー", "分析データがありません。先に分析を実行してください。")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")]
        )
        if path:
            try:
                # --- デバッグ情報出力 ---
                print("--- summary_data for PDF generation ---")
                for key, value in self.summary_data.items():
                    print(f"{key}: ({type(value)}) {value}")
                print("-----------------------------------------")
                # --- デバッグ情報出力ここまで ---

                generate_pdf_report(self.summary_data, path)
                messagebox.showinfo("成功", f"PDFレポートを {path} に保存しました。")
            except Exception as e:
                import traceback
                traceback.print_exc()
                messagebox.showerror("PDF保存エラー", f"PDFの保存に失敗しました:\n{e}")

    def save_wordcloud(self):
        if self.wordcloud_words is None:
            messagebox.showerror("エラー", "分析データがありません。先に分析を実行してください。")
            return

        exclude_words = [word.strip() for word in self.exclude_entry.get().split(',') if word.strip()]

        generate_all = self.wc_all_var.get()
        generate_pos = self.wc_pos_var.get()
        generate_neg = self.wc_neg_var.get()

        if not (generate_all or generate_pos or generate_neg):
            messagebox.showinfo("情報", "生成するワードクラウドの種類が選択されていません。")
            return

        base_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG images", "*.png")],
            title="保存ファイル名 (拡張子なしで入力)"
        )
        if not base_path:
            return

        base_name = os.path.splitext(base_path)[0]
        saved_files = []

        try:
            if generate_all:
                output_path = f"{base_name}_all.png"
                generate_wordcloud(self.wordcloud_words['all'], output_path, exclude_words)
                saved_files.append(output_path)

            if generate_pos:
                output_path = f"{base_name}_positive.png"
                generate_wordcloud(self.wordcloud_words['positive'], output_path, exclude_words)
                saved_files.append(output_path)

            if generate_neg:
                output_path = f"{base_name}_negative.png"
                generate_wordcloud(self.wordcloud_words['negative'], output_path, exclude_words)
                saved_files.append(output_path)

            if saved_files:
                messagebox.showinfo("成功", f"ワードクラウドを保存しました。\n" + "\n".join(saved_files))

        except Exception as e:
            messagebox.showerror("保存エラー", f"ワードクラウドの保存に失敗しました:\n{e}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
