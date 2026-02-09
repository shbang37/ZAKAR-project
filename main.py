import tkinter as tk
from tkinter import messagebox, simpledialog
from analyzer import ZakarEngine
import os
import sys

# 터미널 창 봉쇄 (빌드 후 실행 시 터미널 안 뜸)
if getattr(sys, 'frozen', False):
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

class ZakarGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        # 1. 입력 폴더용 바탕화면 경로
        self.desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        
        # 2. 결과물 저장 위치 (앱이 놓인 실제 폴더 위치 찾기)
        if getattr(sys, 'frozen', False):
            # macOS 앱(.app) 내부에서 실행될 때: 
            # sys.executable은 Zakar.app/Contents/MacOS/Zakar 임
            # 따라서 3단계 위로 올라가야 .app 파일이 있는 폴더가 나옴
            app_inside_path = os.path.dirname(sys.executable)
            contents_dir = os.path.dirname(app_inside_path)
            app_bundle_dir = os.path.dirname(contents_dir)
            self.current_app_dir = os.path.dirname(app_bundle_dir)
        else:
            # 스크립트(.py)로 실행할 때
            self.current_app_dir = os.path.dirname(os.path.abspath(__file__))

    def center_window(self, window, width=450, height=350):
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')
        window.attributes("-topmost", True)

    def run(self):
        try:
            # 1. 입력 폴더 체크 (바탕화면 고정)
            input_folder = os.path.join(self.desktop_path, "01_Zakar_사진넣기")
            
            if not os.path.exists(input_folder):
                os.makedirs(input_folder)
                messagebox.showinfo("Zakar", "바탕화면에 '01_Zakar_사진넣기' 폴더가 생성되었습니다.\n그곳에 사진을 넣고 앱을 다시 실행해주세요.")
                return

            # 2. 행사 이름 입력
            event_name = simpledialog.askstring("Zakar 엔진", "기억할 행사의 이름을 입력하세요:", 
                                                initialvalue="2026_겨울수련회", parent=self.root)
            if not event_name: return

            use_slots = messagebox.askyesno("Zakar 설정", "시간대별로 상세하게 정리할까요?", parent=self.root)

            # 3. 사진 분석 시작
            engine = ZakarEngine(event_name, use_time_slots=use_slots)
            results = engine.run_analysis(input_folder)

            if not results:
                messagebox.showwarning("Zakar", "분석할 사진이 '01_Zakar_사진넣기' 폴더에 없습니다.", parent=self.root)
                return

            # 4. 결과물 폴더 경로 (앱 파일 바로 옆!)
            storage_root = os.path.join(self.current_app_dir, "02_보관용_베스트샷")
            dedup_root = os.path.join(self.current_app_dir, "03_검토용_유사사진")

            # 엔진을 통해 실제 폴더 생성 및 사진 이동
            event_root = engine.organize_initial(
                storage_dir=storage_root,
                dedup_dir=dedup_root,
                results=results
            )

            # 5. 태깅 작업
            self.apply_gui_tagging(event_root)
            
            # 최종 알림 및 폴더 자동 열기
            final_msg = f"✨ 분석 완료!\n\n📂 저장 위치:\n{self.current_app_dir}\n\n[확인]을 누르면 결과 폴더를 엽니다."
            messagebox.showinfo("Zakar 완료", final_msg)
            
            # Finder로 결과물이 담긴 폴더 열기
            os.system(f'open "{self.current_app_dir}"')

        except Exception as e:
            messagebox.showerror("Zakar 오류", f"실행 중 문제가 발생했습니다:\n{str(e)}")
        finally:
            self.root.destroy()
            sys.exit()

    def apply_gui_tagging(self, event_root_path):
        target_folders = []
        for root, dirs, _ in os.walk(event_root_path):
            target_folders.append(root)

        for folder_path in target_folders:
            files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and not f.startswith('.')]
            if not files: continue
            
            folder_name = os.path.basename(folder_path)
            tag_window = tk.Toplevel(self.root)
            tag_window.title(f"태그 입력 - {folder_name}")
            self.center_window(tag_window)
            
            tk.Label(tag_window, text=f"📂 폴더: {folder_name}", font=('AppleGothic', 12, 'bold'), pady=15).pack()
            entry = tk.Entry(tag_window, width=35, font=('AppleGothic', 11))
            entry.pack(pady=5)
            entry.focus_set()

            btn_frame = tk.Frame(tag_window)
            btn_frame.pack(pady=10)
            recoms = ["예배", "찬양", "기도", "식사", "교제", "조별모임", "레크레이션", "섬김"]
            
            def add_tag(tag):
                curr = entry.get().strip()
                if not curr: entry.insert(tk.END, tag)
                elif tag not in curr: entry.insert(tk.END, f", {tag}")

            for i, r_tag in enumerate(recoms):
                tk.Button(btn_frame, text=f"#{r_tag}", command=lambda t=r_tag: add_tag(t), width=7).grid(row=i//4, column=i%4, padx=2, pady=2)

            def submit():
                tags = entry.get()
                tag_suffix = "".join([f"_#{t.strip()}" for t in tags.split(',') if t.strip()]) if tags else ""
                for filename in files:
                    old_path = os.path.join(folder_path, filename)
                    name, ext = os.path.splitext(filename)
                    if tag_suffix not in name:
                        os.rename(old_path, os.path.join(folder_path, f"{folder_name}_{name}{tag_suffix}{ext}"))
                tag_window.destroy()

            tk.Button(tag_window, text="이 폴더 기록 완료", command=submit, bg="#4CAF50", fg="black", width=20, height=2).pack(pady=15)
            tag_window.grab_set()
            self.root.wait_window(tag_window)

if __name__ == "__main__":
    app = ZakarGUI()
    app.run()