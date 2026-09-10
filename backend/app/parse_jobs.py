"""Bounded background parsing with status shared between Gunicorn workers."""
import json
import logging
import multiprocessing
import sqlite3
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
        return db

    def submit(self, filename, content_type, payload, use_ocr):
        job_id = uuid.uuid4().hex
        db = self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM jobs WHERE expires < ?', (time.time(),))
            if db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued', 'running')").fetchone()[0] >= 2:
                raise QueueFull()
            db.execute('INSERT INTO jobs VALUES (?, ?, NULL, NULL, ?)',
                       (job_id, 'queued', time.time() + 7200))
            db.commit()
        finally:
            db.close()
        try:
            # PyMuPDF must not be used concurrently from Python threads.
            multiprocessing.get_context("spawn").Process(
                target=run_job,
                args=(self.path, job_id, filename, content_type, payload, use_ocr),
                daemon=True,
            ).start()
        except Exception:
            self.update(job_id, 'failed', error='Không thể khởi động tác vụ. Hãy thử lại.')
            raise
        return job_id

    def update(self, job_id, status, result=None, error=None):
        db = self.connect()
        try:
            db.execute('UPDATE jobs SET status=?, result=?, error=?, expires=? WHERE id=?',
                       (status, json.dumps(result, ensure_ascii=False) if result is not None else None,
                        error, time.time() + (7200 if status == 'running' else 3600), job_id))
            db.commit()
        finally:
            db.close()

    def run(self, job_id, filename, content_type, payload, use_ocr):
        try:
            self.update(job_id, 'running')
            result = parse_input(filename, content_type, payload, use_ocr)
            self.update(job_id, 'completed', result=result)
        except (ValueError, RuntimeError) as exc:
            self.update(job_id, 'failed', error=str(exc))
        except Exception:
            logging.getLogger(__name__).exception('Parse job %s failed', job_id)
            self.update(job_id, 'failed', error='Xử lý hóa đơn thất bại. Kiểm tra log backend.')

    def get(self, job_id):
        multiprocessing.active_children()  # Reap finished children owned by this worker.
        db = self.connect()
        try:
            row = db.execute('SELECT * FROM jobs WHERE id=? AND expires>=?', (job_id, time.time())).fetchone()
        finally:
            db.close()
        if row is None:
            return None
        return {'id': row['id'], 'status': row['status'], 'error': row['error'],
                'result': json.loads(row['result']) if row['result'] else None}


def run_job(path, job_id, filename, content_type, payload, use_ocr):
    ParseJobs(path).run(job_id, filename, content_type, payload, use_ocr)
