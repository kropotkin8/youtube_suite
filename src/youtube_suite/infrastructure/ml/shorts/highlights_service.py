"""Servicio para detectar momentos interesantes (highlights)"""
import logging
from typing import List, Dict, Any, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer, util
import torch

from youtube_suite.config.settings import get_settings

logger = logging.getLogger(__name__)

# Modelo de embeddings global
_embedding_model: SentenceTransformer = None


def get_embedding_model() -> SentenceTransformer:
    """Obtiene o crea el modelo de embeddings (singleton)"""
    global _embedding_model
    
    if _embedding_model is None:
        name = get_settings().embedding_model
        logger.info(f"Cargando modelo de embeddings: {name}")
        _embedding_model = SentenceTransformer(name)
        logger.info("Modelo de embeddings cargado")
    
    return _embedding_model


def generate_candidate_segments(
    transcription_segments: List[Dict[str, Any]],
    min_duration: float = None,
    max_duration: float = None,
    target_duration: float = None
) -> List[Dict[str, Any]]:
    """
    Genera segmentos candidatos a partir de la transcripción
    
    Args:
        transcription_segments: Segmentos de transcripción
        min_duration: Duración mínima del clip
        max_duration: Duración máxima del clip
        target_duration: Duración objetivo del clip
    
    Returns:
        Lista de segmentos candidatos
    """
    s = get_settings()
    min_duration = min_duration or s.min_clip_duration
    max_duration = max_duration or s.max_clip_duration
    target_duration = target_duration or s.target_clip_duration
    
    candidates = []
    
    # Estrategia: crear segmentos que agrupen oraciones completas
    current_segment = None
    
    for seg in transcription_segments:
        if current_segment is None:
            current_segment = {
                "text": seg["text"],
                "start": seg["start"],
                "end": seg["end"],
                "words": seg.get("words", []),
                "speaker": seg.get("speaker")
            }
        else:
            # Agregar segmento actual
            current_segment["text"] += " " + seg["text"]
            current_segment["end"] = seg["end"]
            if seg.get("words"):
                current_segment["words"].extend(seg["words"])
        
        duration = current_segment["end"] - current_segment["start"]
        
        # Si alcanzamos la duración objetivo o máxima, crear candidato
        if duration >= target_duration or duration >= max_duration:
            if duration >= min_duration:
                candidates.append(current_segment.copy())
            current_segment = None
    
    # Agregar último segmento si existe y cumple requisitos
    if current_segment:
        duration = current_segment["end"] - current_segment["start"]
        if duration >= min_duration:
            candidates.append(current_segment)
    
    logger.info(f"Generados {len(candidates)} segmentos candidatos")
    return candidates


def calculate_semantic_score(
    candidate_text: str,
    full_transcript: str,
    embedding_model: SentenceTransformer
) -> float:
    """
    Calcula score semántico: qué tan representativo es el segmento del contenido total
    
    Args:
        candidate_text: Texto del candidato
        full_transcript: Transcripción completa
        embedding_model: Modelo de embeddings
    
    Returns:
        Score semántico (0.0 a 1.0)
    """
    try:
        # Embeddings
        candidate_emb = embedding_model.encode(candidate_text, convert_to_tensor=True)
        
        # Embedding del documento completo (promedio de chunks)
        # Dividir en chunks para evitar límites de longitud
        chunk_size = 500
        chunks = [full_transcript[i:i+chunk_size] for i in range(0, len(full_transcript), chunk_size)]
        chunk_embs = embedding_model.encode(chunks, convert_to_tensor=True)
        doc_emb = torch.mean(chunk_embs, dim=0)
        
        # Similitud coseno
        similarity = util.cos_sim(candidate_emb.unsqueeze(0), doc_emb.unsqueeze(0)).item()
        
        # Normalizar a 0-1 (cosine similarity ya está en -1 a 1, ajustamos a 0-1)
        score = (similarity + 1) / 2
        
        return float(score)
    except Exception as e:
        logger.warning(f"Error calculando score semántico: {str(e)}")
        return 0.5  # Score neutral


def calculate_energy_score(words: List[Dict[str, Any]]) -> float:
    """
    Calcula score basado en energía (aproximación: longitud de palabras, exclamaciones)
    
    Args:
        words: Lista de palabras con timestamps
    
    Returns:
        Score de energía (0.0 a 1.0)
    """
    if not words:
        return 0.5
    
    # Detectar exclamaciones, palabras en mayúsculas, palabras largas
    exclamation_count = sum(1 for w in words if "!" in w.get("word", ""))
    caps_count = sum(1 for w in words if w.get("word", "").isupper() and len(w.get("word", "")) > 1)
    
    # Normalizar
    total_words = len(words)
    exclamation_ratio = exclamation_count / total_words if total_words > 0 else 0
    caps_ratio = caps_count / total_words if total_words > 0 else 0
    
    # Score combinado
    score = min(1.0, (exclamation_ratio * 2 + caps_ratio) / 2)
    
    return float(score)


def calculate_speaker_change_score(
    candidate: Dict[str, Any],
    all_segments: List[Dict[str, Any]]
) -> float:
    """
    Calcula score basado en cambios de locutor (momentos de diálogo)
    
    Args:
        candidate: Segmento candidato
        all_segments: Todos los segmentos de transcripción
    
    Returns:
        Score de cambio de locutor (0.0 a 1.0)
    """
    if not candidate.get("speaker"):
        return 0.3  # Score bajo si no hay información de speaker
    
    # Buscar segmentos adyacentes con diferentes speakers
    candidate_start = candidate["start"]
    candidate_end = candidate["end"]
    
    # Buscar segmentos justo antes y después
    before_speakers = set()
    after_speakers = set()
    
    for seg in all_segments:
        if seg["end"] <= candidate_start and abs(seg["end"] - candidate_start) < 3.0:
            if seg.get("speaker"):
                before_speakers.add(seg["speaker"])
        elif seg["start"] >= candidate_end and abs(seg["start"] - candidate_end) < 3.0:
            if seg.get("speaker"):
                after_speakers.add(seg["speaker"])
    
    # Si hay cambio de speaker, score alto
    if before_speakers and candidate.get("speaker") not in before_speakers:
        return 1.0
    if after_speakers and candidate.get("speaker") not in after_speakers:
        return 1.0
    
    return 0.5


def calculate_keyword_score(candidate_text: str) -> float:
    """
    Calcula score basado en palabras clave (keywords importantes)
    
    Args:
        candidate_text: Texto del candidato
    
    Returns:
        Score de keywords (0.0 a 1.0)
    """
    # Palabras clave comunes en podcasts (ajustar según necesidad)
    keywords = [
        "importante", "clave", "mejor", "peor", "increíble", "sorprendente",
        "revelación", "descubrimiento", "conclusión", "resumen", "finalmente",
        "no lo vas a creer", "esto es", "lo mejor de", "lo peor de"
    ]
    
    text_lower = candidate_text.lower()
    matches = sum(1 for kw in keywords if kw in text_lower)
    
    # Normalizar (máximo 3 matches = score 1.0)
    score = min(1.0, matches / 3.0)
    
    return float(score)


def calculate_sentiment_score(candidate_text: str) -> float:
    """
    Calcula score basado en sentimiento (aproximación simple)
    
    Args:
        candidate_text: Texto del candidato
    
    Returns:
        Score de sentimiento (0.0 a 1.0)
    """
    # Palabras positivas/emocionales
    positive_words = [
        "genial", "excelente", "fantástico", "increíble", "sorprendente",
        "emocionante", "interesante", "fascinante", "impresionante"
    ]
    
    text_lower = candidate_text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    
    # Normalizar
    score = min(1.0, positive_count / 2.0)
    
    return float(score)


def score_candidates(
    candidates: List[Dict[str, Any]],
    full_transcript: str
) -> List[Dict[str, Any]]:
    """
    Calcula scores para todos los candidatos y los ordena
    
    Args:
        candidates: Lista de candidatos
        full_transcript: Transcripción completa
    
    Returns:
        Lista de candidatos con scores calculados, ordenados por score descendente
    """
    embedding_model = get_embedding_model()
    w = get_settings().score_weights

    scored_candidates = []

    for candidate in candidates:
        # Calcular cada componente del score
        semantic_score = calculate_semantic_score(
            candidate["text"],
            full_transcript,
            embedding_model
        )
        
        energy_score = calculate_energy_score(candidate.get("words", []))
        
        speaker_change_score = calculate_speaker_change_score(
            candidate,
            candidates  # Usar todos los candidatos como contexto
        )
        
        keyword_score = calculate_keyword_score(candidate["text"])
        
        sentiment_score = calculate_sentiment_score(candidate["text"])
        
        # Score combinado con pesos
        total_score = (
            w["semantic"] * semantic_score
            + w["energy"] * energy_score
            + w["speaker_change"] * speaker_change_score
            + w["keyword"] * keyword_score
            + w["sentiment"] * sentiment_score
        )
        
        scored_candidates.append({
            **candidate,
            "score": total_score,
            "score_breakdown": {
                "semantic": semantic_score,
                "energy": energy_score,
                "speaker_change": speaker_change_score,
                "keyword": keyword_score,
                "sentiment": sentiment_score
            }
        })
    
    # Ordenar por score descendente
    scored_candidates.sort(key=lambda x: x["score"], reverse=True)
    
    logger.info(f"Scores calculados para {len(scored_candidates)} candidatos")
    
    return scored_candidates


def select_top_clips(
    scored_candidates: List[Dict[str, Any]],
    num_clips: int = None
) -> List[Dict[str, Any]]:
    """
    Selecciona los mejores clips evitando solapamientos
    
    Args:
        scored_candidates: Candidatos con scores, ordenados
        num_clips: Número de clips a seleccionar
    
    Returns:
        Lista de clips seleccionados
    """
    num_clips = num_clips or get_settings().num_clips

    selected = []
    used_times = []  # Para evitar solapamientos
    
    for candidate in scored_candidates:
        if len(selected) >= num_clips:
            break
        
        start = candidate["start"]
        end = candidate["end"]
        
        # Verificar solapamiento (margen de 5 segundos)
        overlap = False
        for used_start, used_end in used_times:
            if not (end < used_start - 5 or start > used_end + 5):
                overlap = True
                break
        
        if not overlap:
            selected.append(candidate)
            used_times.append((start, end))
    
    logger.info(f"Seleccionados {len(selected)} clips de {len(scored_candidates)} candidatos")
    return selected

