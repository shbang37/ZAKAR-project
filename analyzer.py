import os
import imagehash
from PIL import Image
from tqdm import tqdm
from datetime import datetime
import shutil

class ZakarEngine:
    def __init__(self, event_name, use_time_slots=True):
        self.event_name = event_name
        self.use_time_slots = use_time_slots
        # .heic는 별도의 라이브러리(pyheif 등)가 없으면 Pillow에서 오류가 날 수 있어 예외처리 필요
        self.exts = ('.jpg', '.jpeg', '.png', '.JPG', '.PNG', '.heic', '.HEIC')

    def get_time_slot_name(self, hour):
        if 0 <= hour < 6: return "밤(00-06)"
        elif 6 <= hour < 12: return "오전(06-12)"
        elif 12 <= hour < 18: return "오후(12-18)"
        else: return "저녁(18-24)"

    def get_photo_data(self, image_path):
        try:
            # HEIC 파일 등 라이브러리가 지원하지 않는 포맷일 경우 대비
            with Image.open(image_path) as img:
                hash_val = imagehash.phash(img)
                exif = img._getexif()
                capture_time = None
                # EXIF 촬영 데이터 추출 시도
                if exif and 36867 in exif:
                    try:
                        capture_time = datetime.strptime(exif[36867], '%Y:%m:%d %H:%M:%S')
                    except:
                        capture_time = datetime.fromtimestamp(os.path.getmtime(image_path))
                else:
                    capture_time = datetime.fromtimestamp(os.path.getmtime(image_path))
                return hash_val, capture_time
        except Exception as e:
            # 로그를 남기지 않고 조용히 넘어가거나 에러 출력 가능
            return None, None

    def run_analysis(self, input_folder):
        files = [os.path.join(input_folder, f) for f in os.listdir(input_folder) 
                 if f.lower().endswith(self.exts)]
        
        # GUI 환경을 고려하여 print 대신 로직에 집중
        groups = {}

        for path in tqdm(files, desc="사진 분석 중"):
            h, t = self.get_photo_data(path)
            if h is None or t is None: continue
            
            matched = False
            for master_hash in groups.keys():
                time_diff = abs((t - groups[master_hash][0]['time']).total_seconds())
                
                # 성호 님의 황금 기준: 유사도 20 AND 시간 3초 이내
                if (h - master_hash <= 20) and (time_diff <= 3):
                    groups[master_hash].append({'path': path, 'hash': h, 'time': t})
                    matched = True
                    break
            
            if not matched:
                groups[h] = [{'path': path, 'hash': h, 'time': t}]
        return groups

    def organize_initial(self, storage_dir, dedup_dir, results):
        """
        main.py에서 절대 경로를 받아 실행되도록 경로 결합 방식 최적화
        """
        if not os.path.exists(storage_dir): os.makedirs(storage_dir, exist_ok=True)
        if not os.path.exists(dedup_dir): os.makedirs(dedup_dir, exist_ok=True)

        for master_hash, photo_list in results.items():
            # 용량이 가장 큰 파일을 베스트샷으로 선정
            photo_list.sort(key=lambda x: os.path.getsize(x['path']), reverse=True)
            best = photo_list[0]
            
            date_str = best['time'].strftime('%Y-%m-%d')
            
            if self.use_time_slots:
                slot_name = self.get_time_slot_name(best['time'].hour)
                # 폴더명에 불필요한 괄호 제거 후 생성
                slot_display = slot_name.split('(')[0]
                full_folder_name = f"{date_str}_{slot_display}"
                target_dir = os.path.join(storage_dir, self.event_name, full_folder_name)
            else:
                target_dir = os.path.join(storage_dir, self.event_name, date_str)
                
            os.makedirs(target_dir, exist_ok=True)
            
            # 파일 이동 시 발생할 수 있는 충돌 방지
            dest_path = os.path.join(target_dir, os.path.basename(best['path']))
            if not os.path.exists(dest_path):
                shutil.move(best['path'], dest_path)

            # 유사 사진(중복) 처리
            for extra in photo_list[1:]:
                dedup_dest = os.path.join(dedup_dir, os.path.basename(extra['path']))
                if not os.path.exists(dedup_dest):
                    shutil.move(extra['path'], dedup_dest)
        
        return os.path.join(storage_dir, self.event_name)

    # GUI에서 태깅을 처리하므로 이 함수는 더 이상 사용되지 않지만, 터미널용으로 남겨둠
    def apply_tags_and_rename(self, event_root_path):
        # ... (기존 코드 유지 또는 삭제 가능)
        pass