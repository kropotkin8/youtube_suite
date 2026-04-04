"""Servicio para extracción y edición de clips de video"""
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def extract_clip(
    input_video: str,
    start_time: float,
    duration: float,
    output_path: str,
    fade_in: float = 0.5,
    fade_out: float = 0.5
) -> str:
    """
    Extrae un clip de video usando FFmpeg
    
    Args:
        input_video: Ruta al video original
        start_time: Tiempo de inicio en segundos
        duration: Duración del clip en segundos
        output_path: Ruta de salida
        fade_in: Duración del fade in en segundos
        fade_out: Duración del fade out en segundos
    
    Returns:
        Ruta al clip generado
    """
    try:
        # FFmpeg command con fades opcionales
        # Usar -ss antes de -i para velocidad (seeking rápido)
        # -c copy para copiar streams sin recodificar (rápido pero menos preciso)
        # Si necesitas precisión de frame, usa -ss después de -i (más lento)
        
        if fade_in > 0 or fade_out > 0:
            # Con fades (requiere recodificación)
            cmd = [
                "ffmpeg",
                "-y",
                "-ss", str(start_time),
                "-i", input_video,
                "-t", str(duration),
                "-vf", f"fade=t=in:st=0:d={fade_in},fade=t=out:st={duration-fade_out}:d={fade_out}",
                "-af", f"afade=t=in:st=0:d={fade_in},afade=t=out:st={duration-fade_out}:d={fade_out}",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "fast",
                output_path
            ]
        else:
            # Sin fades (copiar streams, más rápido)
            cmd = [
                "ffmpeg",
                "-y",
                "-ss", str(start_time),
                "-i", input_video,
                "-t", str(duration),
                "-c", "copy",  # Copiar sin recodificar
                output_path
            ]
        
        logger.info(f"Extrayendo clip: {start_time}s - {start_time + duration}s")
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        if not Path(output_path).exists():
            raise FileNotFoundError(f"El clip no se creó: {output_path}")
        
        logger.info(f"Clip generado exitosamente: {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error al extraer clip: {e.stderr}")
        raise RuntimeError(f"Error al extraer clip: {e.stderr}")
    except Exception as e:
        logger.error(f"Error inesperado al extraer clip: {str(e)}")
        raise


def extract_multiple_clips(
    input_video: str,
    clips: List[Dict[str, Any]],
    output_dir: str,
    base_filename: str = "clip"
) -> List[Dict[str, Any]]:
    """
    Extrae múltiples clips de un video
    
    Args:
        input_video: Ruta al video original
        clips: Lista de clips a extraer, cada uno con start, end, y metadata
        output_dir: Directorio de salida
        base_filename: Nombre base para los archivos
    
    Returns:
        Lista de clips con información de ruta actualizada
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    extracted_clips = []
    
    for i, clip in enumerate(clips):
        start = clip["start"]
        end = clip["end"]
        duration = end - start
        
        # Nombre del archivo
        clip_filename = f"{base_filename}_{i+1:03d}_{int(start)}s_{int(end)}s.mp4"
        clip_path = output_path / clip_filename
        
        try:
            extract_clip(
                input_video,
                start,
                duration,
                str(clip_path),
                fade_in=0.5,
                fade_out=0.5
            )
            
            extracted_clips.append({
                **clip,
                "path": str(clip_path),
                "filename": clip_filename
            })
            
        except Exception as e:
            logger.error(f"Error al extraer clip {i+1}: {str(e)}")
            # Continuar con el siguiente clip
    
    logger.info(f"Extraídos {len(extracted_clips)} de {len(clips)} clips")
    return extracted_clips

