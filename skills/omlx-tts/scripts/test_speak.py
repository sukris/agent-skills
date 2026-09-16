"""Run with: python3 -m unittest discover -s scripts -p 'test_*.py'."""
import io
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch, MagicMock
import wave

from speak import speak, main


class SpeakTest(unittest.TestCase):
    def test_temporary_audio_cleanup_and_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory) / "omlx-tts-test"
            audio = temporary / "speech.wav"
            def generate(text, output, *args):
                Path(output).write_bytes(b"test audio")
                return {"path": output, "duration_seconds": 2}
            with patch("speak.tempfile.mkdtemp", return_value=str(temporary)), \
                 patch("speak.speak", side_effect=generate) as synthesize, \
                 patch("speak.subprocess.run") as run, \
                 patch("sys.stdout", new_callable=io.StringIO), \
                 patch("sys.stderr", new_callable=io.StringIO), \
                 patch("sys.argv", ["speak.py", "--text", "你好", "--play"]):
                temporary.mkdir()
                self.assertEqual(main(), 0)
                self.assertFalse(temporary.exists())
                temporary.mkdir()
                run.side_effect = subprocess.CalledProcessError(1, "afplay")
                self.assertEqual(main(), 1)
                self.assertEqual(audio.read_bytes(), b"test audio")
                audio.unlink()
                synthesize.side_effect = RuntimeError("generation failed")
                self.assertEqual(main(), 1)
                self.assertFalse(temporary.exists())
                kept = Path(directory) / "keep.wav"
                synthesize.side_effect = generate
                run.side_effect = None
                with patch("sys.argv", ["speak.py", "--text", "你好", "--play", "--output", str(kept)]):
                    self.assertEqual(main(), 0)
                    self.assertEqual(kept.read_bytes(), b"test audio")

    def test_playback_is_opt_in_and_reports_failure(self):
        result = {"path": "/tmp/语音 文件.wav", "duration_seconds": 2}
        with patch("speak.speak", return_value=result), patch("speak.subprocess.run") as run, \
             patch("sys.stdout", new_callable=io.StringIO), patch("sys.stderr", new_callable=io.StringIO) as errors:
            args = ["speak.py", "--text", "你好", "--output", result["path"]]
            with patch("sys.argv", args):
                self.assertEqual(main(), 0)
                run.assert_not_called()
            with patch("sys.argv", args + ["--play"]):
                self.assertEqual(main(), 0)
                run.assert_called_once_with(["/usr/bin/afplay", result["path"]], check=True, timeout=30)
                run.side_effect = subprocess.CalledProcessError(1, "/usr/bin/afplay")
                self.assertEqual(main(), 1)
                self.assertIn("音频已保存，但播放失败", errors.getvalue())

    def test_http_contract_and_failed_responses_preserve_files(self):
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
            wav.writeframes(b"\x01\x00" * 240)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / "settings.json"
            settings.write_text(json.dumps({"server": {"port": 8123}, "auth": {"api_key": "test-secret"}}))
            output = root / "speech.wav"
            response = MagicMock(status=200)
            response.read.return_value = buffer.getvalue()
            with patch("speak.http.client.HTTPConnection") as factory:
                connection = factory.return_value
                connection.getresponse.return_value = response
                result = speak("你好", output, settings, voice="serena")
                factory.assert_called_with("127.0.0.1", 8123, timeout=300)
                method, endpoint, body, headers = connection.request.call_args.args
                self.assertEqual((method, endpoint), ("POST", "/v1/audio/speech"))
                self.assertEqual(json.loads(body)["input"], "你好")
                self.assertEqual(json.loads(body)["voice"], "serena")
                self.assertEqual(headers["Authorization"], "Bearer test-secret")
                self.assertEqual(result["duration_seconds"], 0.01)
                self.assertEqual(output.read_bytes(), buffer.getvalue())
                with self.assertRaises(FileExistsError):
                    speak("不要覆盖", output, settings)
                self.assertEqual(connection.request.call_count, 1)
                response.status = 401
                response.read.return_value = b"invalid test-secret"
                with self.assertRaisesRegex(RuntimeError, r"HTTP 401: invalid \[REDACTED\]"):
                    speak("你好", root / "error.wav", settings)
                self.assertFalse((root / "error.wav").exists())
                response.status = 200
                response.read.return_value = b"this is not audio"
                with self.assertRaises(wave.Error):
                    speak("你好", root / "invalid.wav", settings)
                self.assertFalse((root / "invalid.wav").exists())
                with self.assertRaises(ValueError):
                    speak(" ", root / "empty.wav", settings)


if __name__ == "__main__":
    unittest.main()
