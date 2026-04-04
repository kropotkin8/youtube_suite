"""Servicio para extracción y procesamiento de audio"""
import subprocess
import shlex
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def extract_audio(video_path: str, output_path: str, sample_rate: int = 16000, channels: int = 1) -> str:
    """
    Extrae audio de un video usando FFmpeg
    
    Args:
        video_path: Ruta al video
        output_path: Ruta de salida para el audio (WAV)
        sample_rate: Sample rate del audio (default: 16000)
        channels: Número de canales (1=mono, 2=stereo)
    
    Returns:
        Ruta al archivo de audio extraído
    """
    try:
        # FFmpeg command: extraer audio, convertir a mono, resamplear
        cmd = [
            "ffmpeg",
            "-y",  # Sobrescribir si existe
            "-i", video_path,
            "-ac", str(channels),  # Canales
            "-ar", str(sample_rate),  # Sample rate
            "-vn",  # No video
            output_path
        ]
        
        logger.info(f"Extrayendo audio de {video_path} a {output_path}")
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        if not Path(output_path).exists():
            raise FileNotFoundError(f"El archivo de audio no se creó: {output_path}")
        
        logger.info(f"Audio extraído exitosamente: {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error al extraer audio: {e.stderr}")
        raise RuntimeError(f"Error al extraer audio: {e.stderr}")
    except Exception as e:
        logger.error(f"Error inesperado al extraer audio: {str(e)}")
        raise


def get_audio_duration(audio_path: str) -> float:
    """
    Obtiene la duración de un archivo de audio usando FFprobe
    
    Args:
        audio_path: Ruta al archivo de audio
    
    Returns:
        Duración en segundos
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        duration = float(result.stdout.strip())
        return duration
        
    except Exception as e:
        logger.warning(f"No se pudo obtener duración del audio: {str(e)}")
        return 0.0

