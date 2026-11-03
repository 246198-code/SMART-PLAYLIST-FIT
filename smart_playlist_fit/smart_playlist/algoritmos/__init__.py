"""Algoritmos del proyecto Smart Playlist (implementados por el grupo, sin sort()/sorted())."""
from .busqueda import buscar_por_prefijo
from .dinamica import generar_playlist_pd, tabla_dp
from .greedy import generar_playlist_greedy
from .ordenamiento import CRITERIOS, merge_sort, ordenar_canciones

__all__ = ["CRITERIOS", "merge_sort", "ordenar_canciones",
           "generar_playlist_greedy", "generar_playlist_pd", "tabla_dp", "buscar_por_prefijo"]
