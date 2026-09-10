"""Bounded background parsing with status shared between Gunicorn workers."""
import json
import logging
import multiprocessing
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path

from .parser import parse_input


class QueueFull(Exception):
    pass


class ParseJobs:
    def __init__(self, path):
        self.path = str(path)

    def connect(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, status TEXT, result TEXT, error TEXT, expires REAL)')
        db.execute('CREATE TABLE IF NOT EXISTS job_progress (id TEXT PRIMARY KEY, heartbeat REAL, message TEXT)')
        return db

    def submit(self, filename, content_type, payload, use_ocr):
        job_id = uuid.uuid4().hex
        db = self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM jobs WHERE expires < ?', (time.time(),))
            db.execute('DELETE FROM job_progress WHERE id NOT IN (SELECT id FROM jobs)')
            self.fail_stale(db)
            if db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued', 'running')").fetchone()[0] >= max(1, int(os.getenv('PARSE_MAX_ACTIVE', '1'))):
                raise QueueFull()
            db.execute('INSERT INTO jobs VALUES (?, ?, NULL, NULL, ?)',
                       (job_id, 'queued', time.time() + 7200))
            db.execute('INSERT INTO job_progress VALUES (?, ?, ?)', (job_id, time.time(), 'Đang khởi động OCR...'))
            db.commit()
        finally:
            db.close()
        try:
            # PyMuPDF must not be used concurrently from Python threads.
            process = multiprocessing.get_context("spawn").Process(
                target=run_job,
                args=(self.path, job_id, filename, content_type, payload, use_ocr),
                daemon=True,
            )
            process.start()
            threading.Thread(target=self.monitor, args=(job_id, process), daemon=True).start()
        except Exception:
            self.update(job_id, 'failed', error='Không thể khởi động tác vụ. Hãy thử lại.')
            raise
        return job_id

    @staticmethod
    def fail_stale(db):
        db.execute("""UPDATE jobs SET status='failed', error=?, expires=?
                      WHERE status IN ('queued','running') AND id NOT IN
                      (SELECT id FROM job_progress WHERE heartbeat > ?)""",
                   ('Tiến trình OCR đã mất liên lạc hoặc backend đã khởi động lại. Hãy thử lại file.',
                    time.time() + 3600, time.time() - 120))

    def report(self, job_id, message=None):
        db = self.connect()
        try:
            db.execute('UPDATE job_progress SET heartbeat=?, message=COALESCE(?, message) WHERE id=?',
                       (time.time(), message, job_id))
            db.commit()
        finally:
            db.close()

    def monitor(self, job_id, process):
        deadline = time.monotonic() + int(os.getenv('PARSE_JOB_TIMEOUT', '1800'))
        try:
            while process.is_alive():
                self.report(job_id)
                if time.monotonic() > deadline:
                    process.terminate()
                    process.join(5)
                    if process.is_alive():
                        process.kill()
                    self.update(job_id, 'failed', error='OCR vượt thời gian cho phép. Hãy thử PDF ít trang hơn.')
                    break
                process.join(5)
            process.join()
            # A killed/OOM child cannot catch exceptions or publish its result.
            self.update(job_id, 'failed', error=f'Tiến trình OCR đã dừng (mã {process.exitcode}). Kiểm tra RAM và log Colab.')
        except Exception:
            logging.getLogger(__name__).exception('Monitor for job %s failed', job_id)
        finally:
            if not process.is_alive():
                process.close()

    def update(self, job_id, status, result=None, error=None):
        db = self.connect()
        try:
            db.execute("UPDATE jobs SET status=?, result=?, error=?, expires=? WHERE id=? AND status IN ('queued','running')",
                       (status, json.dumps(result, ensure_ascii=False) if result is not None else None,
                        error, time.time() + (7200 if status == 'running' else 3600), job_id))
            db.commit()
        finally:
            db.close()

    def run(self, job_id, filename, content_type, payload, use_ocr):
        try:
            self.update(job_id, 'running')
            logging.getLogger(__name__).warning('OCR job %s started (pid %s)', job_id, os.getpid())
            result = parse_input(filename, content_type, payload, use_ocr,
                                 progress=lambda message: self.report(job_id, message))
            self.update(job_id, 'completed', result=result)
            logging.getLogger(__name__).warning('OCR job %s completed', job_id)
        except (ValueError, RuntimeError) as exc:
            logging.getLogger(__name__).warning('OCR job %s failed: %s', job_id, exc)
            self.update(job_id, 'failed', error=str(exc))
        except Exception:
            logging.getLogger(__name__).exception('Parse job %s failed', job_id)
            self.update(job_id, 'failed', error='Xử lý hóa đơn thất bại. Kiểm tra log backend.')

    def get(self, job_id, include_result=True):
        db = self.connect()
        try:
            self.fail_stale(db)
            db.commit()
            result_column = ', jobs.result' if include_result else ''
            row = db.execute(f'''SELECT jobs.id, jobs.status, jobs.error, job_progress.message{result_column}
                                 FROM jobs LEFT JOIN job_progress ON jobs.id=job_progress.id
                                 WHERE jobs.id=? AND expires>=?''', (job_id, time.time())).fetchone()
        finally:
            db.close()
        if row is None:
            return None
        job = {'id': row['id'], 'status': row['status'], 'error': row['error'], 'message': row['message']}
        if include_result:
            job['result'] = json.loads(row['result']) if row['result'] else None
        return job


def run_job(path, job_id, filename, content_type, payload, use_ocr):
    # Prevent Tesseract/OpenCV oversubscribing the small Colab CPU allocation.
    os.environ.setdefault('OMP_THREAD_LIMIT', '1')
    import cv2
    cv2.setNumThreads(1)
    ParseJobs(path).run(job_id, filename, content_type, payload, use_ocr)
