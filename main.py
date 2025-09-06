import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json
from datetime import datetime
import re
import threading
from PIL import Image, ImageTk
import io
import os
import sys
import firebase_admin
from firebase_admin import credentials, db, storage
import urllib.request
import tempfile
import webbrowser
from urllib.parse import urlparse, parse_qs
import logging
import time
import cv2
import numpy as np
import subprocess
from queue import Queue, Empty
import shutil
import vlc

# Définition des couleurs principales en dehors de la classe (couleurs douces pour les yeux)
BG_COLOR = "#2c3e50"  # Bleu-gris foncé
CARD_COLOR = "#34495e"  # Bleu-gris moyen
LIGHT_CARD_COLOR = "#3d566e"  # Bleu-gris clair
PINK_COLOR = "#e74c3c"  # Rouge doux pour les éléments importants
TEXT_COLOR = "#ecf0f1"  # Texte blanc cassé doux
MUTED_COLOR = "#bdc3c7"  # Texte gris doux pour les éléments secondaires
ACCENT_COLOR = "#3498db"  # Bleu doux pour les accents
ACCENT_LIGHT = "#5dade2"  # Bleu clair
SUCCESS_COLOR = "#2ecc71"  # Vert doux pour le succès
DANGER_COLOR = "#e74c3c"  # Rouge doux pour le danger
WARNING_COLOR = "#f39c12"  # Orange doux pour les avertissements
PURPLE_COLOR = "#9b59b6"  # Violet doux
# Configuration Firebase
FIREBASE_CONFIG = {
    "project_info": {
        "project_number": "471965282940",
        "firebase_url": "https://djezzy-bd229-default-rtdb.firebaseio.com",
        "project_id": "djezzy-bd229",
        "storage_bucket": "djezzy-bd229.firebasestorage.app"
    },
    "client": [
        {
            "client_info": {
                "mobilesdk_app_id": "1:471965282940:android:96106b61c3b19e415b0ff9",
                "android_client_info": {
                    "package_name": "com.hamza.ziadi"
                }
            },
            "oauth_client": [],
            "api_key": [
                {
                    "current_key": "AIzaSyBJnRj0VHT7n-g8CqcwblKWroZYZp4L0iI"
                }
            ],
            "services": {
                "appinvite_service": {
                    "other_platform_oauth_client": []
                }
            }
        }
    ],
    "configuration_version": "1"
}
def check_vlc():
    """Vérifier si VLC est installé sur le système"""
    try:
        # Essayer de créer une instance VLC
        instance = vlc.Instance()
        player = instance.media_player_new()
        logging.info("VLC trouvé sur le système")
        return True
    except Exception as e:
        logging.error(f"VLC non trouvé: {str(e)}")
        return False

class InternalPlayer:
    """Lecteur vidéo interne intégré"""
    def __init__(self, video_frame, status_callback=None):
        self.video_frame = video_frame
        self.status_callback = status_callback
        self.is_playing = False
        self.current_channel = None
        self.video_thread = None
        self.frame_queue = Queue(maxsize=30)
        self.stop_event = threading.Event()
        self.volume = 80
        self.muted = False
        self.vlc_available = check_vlc()
        
        # Configuration du cadre vidéo
        self.video_label = tk.Label(self.video_frame, bg="black")
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # Configuration du traitement vidéo
        self.cap = None
        self.current_image = None
        
        # Configuration du lecteur VLC
        if self.vlc_available:
            try:
                self.vlc_instance = vlc.Instance()
                self.vlc_player = self.vlc_instance.media_player_new()
                # Lier le lecteur au cadre vidéo
                if sys.platform == "win32":
                    self.vlc_player.set_hwnd(self.video_frame.winfo_id())
                else:
                    self.vlc_player.set_xwindow(self.video_frame.winfo_id())
                logging.info("Lecteur VLC initialisé avec succès")
            except Exception as e:
                logging.error(f"Échec de l'initialisation du lecteur VLC: {str(e)}")
                self.vlc_available = False
        
    def play(self, stream_url, channel_name):
        """Lire une chaîne"""
        try:
            # Arrêter toute lecture en cours
            self.stop()
            
            self.current_channel = channel_name
            self.is_playing = True
            self.stop_event.clear()
            
            # Mettre à jour le statut
            if self.status_callback:
                self.status_callback(f"Lecture de la chaîne: {channel_name}")
            
            # Enregistrer l'URL pour le débogage
            logging.info(f"Tentative de lecture de la chaîne: {channel_name} depuis l'URL: {stream_url}")
            
            # Vérifier si VLC est disponible
            if self.vlc_available:
                # Utiliser VLC pour lire la vidéo
                try:
                    media = self.vlc_instance.media_new(stream_url)
                    self.vlc_player.set_media(media)
                    self.vlc_player.play()
                    
                    # Régler le volume
                    self.vlc_player.audio_set_volume(self.volume)
                    
                    # Démarrer la mise à jour de l'interface
                    self.update_player_status()
                    
                    logging.info(f"Démarrage de la lecture avec VLC: {channel_name}")
                    return
                except Exception as e:
                    logging.error(f"Échec de la lecture avec VLC: {str(e)}")
            
            # Utiliser une méthode alternative si VLC n'est pas disponible
            logging.warning("VLC non disponible, utilisation d'une méthode alternative")
            
            # Afficher un message à l'utilisateur
            if self.status_callback:
                self.status_callback(f"Lecture de la chaîne: {channel_name} (méthode alternative)")
            
            # Essayer d'ouvrir la vidéo dans le navigateur par défaut
            try:
                webbrowser.open(stream_url)
                logging.info(f"URL ouverte dans le navigateur: {stream_url}")
                return
            except Exception as e:
                logging.error(f"Échec de l'ouverture de l'URL dans le navigateur: {str(e)}")
                if self.status_callback:
                    self.status_callback(f"Échec de la lecture de la chaîne: {channel_name}")
                return
            
        except Exception as e:
            logging.error(f"Erreur lors de la lecture de la chaîne: {str(e)}")
            if self.status_callback:
                self.status_callback(f"Erreur lors de la lecture de la chaîne: {channel_name}")
    
    def update_player_status(self):
        """Mettre à jour le statut du lecteur"""
        try:
            if self.is_playing and self.vlc_available:
                # Vérifier l'état du lecteur
                state = self.vlc_player.get_state()
                
                if state == vlc.State.Playing:
                    if self.status_callback:
                        self.status_callback(f"En cours: {self.current_channel}")
                elif state == vlc.State.Paused:
                    if self.status_callback:
                        self.status_callback(f"En pause: {self.current_channel}")
                elif state == vlc.State.Stopped or state == vlc.State.Ended:
                    if self.status_callback:
                        self.status_callback(f"Arrêté: {self.current_channel}")
                    self.is_playing = False
                elif state == vlc.State.Error:
                    if self.status_callback:
                        self.status_callback(f"Erreur de lecture: {self.current_channel}")
                    self.is_playing = False
                
                # Continuer la mise à jour
                if self.is_playing:
                    self.video_frame.after(1000, self.update_player_status)
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour du statut du lecteur: {str(e)}")
    
    def stop(self):
        """Arrêter le lecteur"""
        self.is_playing = False
        self.stop_event.set()
        
        if self.vlc_available and self.vlc_player:
            try:
                self.vlc_player.stop()
            except Exception as e:
                logging.error(f"Erreur lors de l'arrêt du lecteur VLC: {str(e)}")
        
        # Effacer le cadre
        self.video_label.config(image='')
        self.current_image = None
        
        if self.status_callback:
            self.status_callback("Lecteur arrêté")
        
        logging.info("Lecteur arrêté avec succès")
    
    def set_volume(self, volume):
        """Régler le volume"""
        self.volume = volume
        if self.vlc_available and self.vlc_player:
            try:
                self.vlc_player.audio_set_volume(int(volume))
            except Exception as e:
                logging.error(f"Erreur lors du réglage du volume: {str(e)}")
        logging.info(f"Volume réglé à: {volume}")
    
    def toggle_mute(self):
        """Basculer le mode muet"""
        self.muted = not self.muted
        if self.vlc_available and self.vlc_player:
            try:
                self.vlc_player.audio_set_mute(self.muted)
            except Exception as e:
                logging.error(f"Erreur lors de l'activation du mode muet: {str(e)}")
        logging.info(f"Mode muet: {self.muted}")
    
    def is_playing_status(self):
        """Vérifier l'état de lecture"""
        return self.is_playing

class IPTVPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LECTEUR IPTV-V-1.0.0")
        self.root.geometry("1400x800")  # Taille plus grande
        self.root.configure(bg=BG_COLOR)
        
        # Enregistrer le démarrage
        logging.info("Démarrage de l'application IPTV Player")
        
        # Configuration des couleurs
        self.bg_color = BG_COLOR
        self.card_color = CARD_COLOR
        self.light_card_color = LIGHT_CARD_COLOR
        self.pink_color = PINK_COLOR
        self.text_color = TEXT_COLOR
        self.muted_color = MUTED_COLOR
        self.accent_color = ACCENT_COLOR
        self.accent_light = ACCENT_LIGHT
        self.success_color = SUCCESS_COLOR
        self.danger_color = DANGER_COLOR
        self.warning_color = WARNING_COLOR
        self.purple_color = PURPLE_COLOR
        
        # Configuration de Firebase
        self.firebase_initialized = False
        self.setup_firebase()
        
        # Configuration des variables de l'application (valeurs par défaut)
        self.base_url = ""
        self.username = ""
        self.password = ""
        self.api_url = ""
        self.subscription_codes = []
        self.update_info = {}
        
        # Données des chaînes et catégories
        self.categories = []
        self.channels = []
        self.selected_category = None
        self.selected_channel = None
        
        # Configuration du lecteur principal
        self.player = None
        
        # Variables de vérification d'abonnement
        self.subscription_active = False
        self.subscription_end_date = None
        
        # Variables de plein écran et deuxième lecteur
        self.is_fullscreen = False
        self.normal_geometry = ""
        self.secondary_player_window = None
        self.secondary_player = None
        self.secondary_status_var = None
        
        # Configuration de l'icône de l'application
        self.set_app_icon()
        
        # Charger les données depuis Firebase
        self.load_data_from_firebase()
        
        # Vérifier les mises à jour
        if self.firebase_initialized:
            self.check_for_updates()
        else:
            # Utiliser une méthode alternative pour vérifier les mises à jour
            self.check_for_updates_alternative()
        
        # Créer l'interface utilisateur
        self.create_login_screen()
        
        logging.info("Application initialisée avec succès")
    
    def setup_firebase(self):
        """Configurer la connexion à Firebase"""
        try:
            # Initialiser Firebase si ce n'est pas déjà fait
            if not firebase_admin._apps:
                # Essayer d'utiliser un fichier JSON de clé de service s'il existe
                try:
                    if os.path.exists("serviceAccountKey.json"):
                        cred = credentials.Certificate("serviceAccountKey.json")
                        firebase_admin.initialize_app(cred, {
                            'databaseURL': FIREBASE_CONFIG["project_info"]["firebase_url"],
                            'storageBucket': FIREBASE_CONFIG["project_info"]["storage_bucket"]
                        })
                        self.firebase_initialized = True
                        logging.info("Connecté à Firebase avec succès en utilisant le fichier JSON")
                    else:
                        # Utiliser la méthode d'authentification automatique
                        firebase_admin.initialize_app(options={
                            'databaseURL': FIREBASE_CONFIG["project_info"]["firebase_url"],
                            'storageBucket': FIREBASE_CONFIG["project_info"]["storage_bucket"]
                        })
                        self.firebase_initialized = True
                        logging.info("Connecté à Firebase avec succès en utilisant l'authentification automatique")
                except Exception as e:
                    logging.error(f"Échec de la connexion à Firebase: {str(e)}")
                    self.firebase_initialized = False
            
            # Obtenir les références de base de données et de stockage si l'initialisation a réussi
            if self.firebase_initialized:
                self.db_ref = db.reference()
                try:
                    self.storage_bucket = storage.bucket()
                    logging.info("Connecté au stockage Firebase avec succès")
                except Exception as e:
                    self.storage_bucket = None
                    logging.error(f"Échec de la connexion au stockage Firebase: {str(e)}")
        except Exception as e:
            logging.error(f"Erreur lors de la configuration de Firebase: {str(e)}")
            self.firebase_initialized = False
    
    def load_data_from_firebase(self):
        """Charger les données depuis Firebase"""
        try:
            if self.firebase_initialized and hasattr(self, 'db_ref'):
                # Obtenir toutes les données depuis Firebase
                data_ref = self.db_ref.get()
                
                if data_ref:
                    # Charger la configuration de l'API
                    api_config = data_ref.get('api_config', {})
                    if api_config:
                        self.base_url = api_config.get('base_url', '')
                        self.username = api_config.get('username', '')
                        self.password = api_config.get('password', '')
                        self.api_url = api_config.get('api_url', f"{self.base_url}/player_api.php?&username={self.username}&password={self.password}")
                    
                    # Charger les informations de mise à jour
                    self.update_info = data_ref.get('updates', {})
                    
                    # Charger les informations d'abonnement
                    subscriptions_data = data_ref.get('subscriptions', {})
                    if subscriptions_data:
                        self.subscription_codes = []
                        for sub_id, sub_data in subscriptions_data.items():
                            if sub_data.get('active', False):
                                code = sub_data.get('code', '')
                                if code:
                                    self.subscription_codes.append(code)
                    
                    logging.info("Données chargées depuis Firebase avec succès")
                else:
                    logging.warning("Aucune donnée trouvée dans Firebase")
            else:
                # Utiliser une requête HTTP directe
                response = requests.get("https://djezzy-bd229-default-rtdb.firebaseio.com/.json", timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Charger la configuration de l'API
                    api_config = data.get('api_config', {})
                    if api_config:
                        self.base_url = api_config.get('base_url', '')
                        self.username = api_config.get('username', '')
                        self.password = api_config.get('password', '')
                        self.api_url = api_config.get('api_url', f"{self.base_url}/player_api.php?&username={self.username}&password={self.password}")
                    
                    # Charger les informations de mise à jour
                    self.update_info = data.get('updates', {})
                    
                    # Charger les informations d'abonnement
                    subscriptions_data = data.get('subscriptions', {})
                    if subscriptions_data:
                        self.subscription_codes = []
                        for sub_id, sub_data in subscriptions_data.items():
                            if sub_data.get('active', False):
                                code = sub_data.get('code', '')
                                if code:
                                    self.subscription_codes.append(code)
                    
                    logging.info("Données chargées depuis Firebase avec succès (méthode alternative)")
                else:
                    logging.warning("Échec du chargement des données depuis Firebase")
        except Exception as e:
            logging.error(f"Erreur lors du chargement des données depuis Firebase: {str(e)}")
    
    def refresh_data_from_firebase(self):
        """Recharger les données depuis Firebase"""
        try:
            self.load_data_from_firebase()
            
            # Mettre à jour l'interface utilisateur
            if hasattr(self, 'status_var'):
                self.status_var.set("Données mises à jour avec succès")
            
            # Si l'utilisateur est connecté, recharger la liste des chaînes
            if self.subscription_active and hasattr(self, 'load_data'):
                self.load_data()
            
            logging.info("Données rechargées depuis Firebase avec succès")
            return True
        except Exception as e:
            logging.error(f"Erreur lors du rechargement des données depuis Firebase: {str(e)}")
            if hasattr(self, 'status_var'):
                self.status_var.set("Échec de la mise à jour des données")
            return False
    
    def check_for_updates_alternative(self):
        """Méthode alternative pour vérifier les mises à jour sans Firebase"""
        try:
            # Utiliser une requête HTTP directe pour vérifier les mises à jour
            response = requests.get("https://djezzy-bd229-default-rtdb.firebaseio.com/updates.json", timeout=5)
            
            if response.status_code == 200:
                update_info = response.json()
                
                if update_info:
                    current_version = "1.0.0"  # Version actuelle de l'application
                    latest_version = update_info.get('version', '1.0.0')
                    update_url = update_info.get('url', '')
                    update_message = update_info.get('message', 'Une nouvelle version de l\'application est disponible')
                    
                    if latest_version > current_version and update_url:
                        # Afficher un message de mise à jour
                        result = messagebox.askyesno(
                            "Mise à jour disponible",
                            f"{update_message}\nVersion actuelle: {current_version}\nNouvelle version: {latest_version}\n\nVoulez-vous mettre à jour l'application maintenant ?"
                        )
                        
                        if result:
                            self.open_update_link(update_url)
                    else:
                        # Afficher un message d'absence de mise à jour
                        messagebox.showinfo(
                            "Mises à jour",
                            "Votre application est déjà à jour avec la dernière version disponible."
                        )
                else:
                    # Afficher un message d'absence d'informations de mise à jour
                    messagebox.showinfo(
                        "Mises à jour",
                        "Aucune information sur les mises à jour n'est disponible pour le moment."
                    )
        except Exception as e:
            logging.error(f"Erreur lors de la vérification des mises à jour (méthode alternative): {str(e)}")
            # Afficher un message d'erreur clair
            messagebox.showerror(
                "Erreur de connexion",
                "Échec de la connexion au serveur de mises à jour. Veuillez vérifier votre connexion Internet et réessayer plus tard."
            )
    
    def check_for_updates(self):
        """Vérifier les mises à jour de l'application"""
        if not self.firebase_initialized:
            self.check_for_updates_alternative()
            return
            
        try:
            # Obtenir les informations de mise à jour depuis Firebase
            updates_ref = self.db_ref.child('updates')
            update_info = updates_ref.get()
            
            if update_info:
                current_version = "1.0.0"  # Version actuelle de l'application
                latest_version = update_info.get('version', '1.0.0')
                update_url = update_info.get('url', '')
                update_message = update_info.get('message', 'Une nouvelle version de l\'application est disponible')
                
                if latest_version > current_version and update_url:
                    # Afficher un message de mise à jour
                    result = messagebox.askyesno(
                        "Mise à jour disponible",
                        f"{update_message}\nVersion actuelle: {current_version}\nNouvelle version: {latest_version}\n\nVoulez-vous mettre à jour l'application maintenant ?"
                    )
                    
                    if result:
                        self.open_update_link(update_url)
                else:
                    # Afficher un message d'absence de mise à jour
                    messagebox.showinfo(
                        "Mises à jour",
                        "Votre application est déjà à jour avec la dernière version disponible."
                    )
            else:
                # Afficher un message d'absence d'informations de mise à jour
                messagebox.showinfo(
                    "Mises à jour",
                    "Aucune information sur les mises à jour n'est disponible pour le moment."
                )
        except Exception as e:
            logging.error(f"Erreur lors de la vérification des mises à jour: {str(e)}")
            # Afficher un message d'erreur clair
            messagebox.showerror(
                "Erreur de connexion",
                "Échec de la connexion au serveur de mises à jour. Veuillez vérifier votre connexion Internet et réessayer plus tard."
            )
            # Utiliser la méthode alternative en cas d'échec
            self.check_for_updates_alternative()
    
    def is_valid_url(self, url):
        """Vérifier la validité de l'URL"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception as e:
            logging.error(f"Erreur lors de la vérification de la validité de l'URL: {str(e)}")
            return False
    
    def open_update_link(self, update_url):
        """Ouvrir le lien de mise à jour dans le navigateur"""
        try:
            # Vérifier la validité du lien
            if not self.is_valid_url(update_url):
                messagebox.showerror(
                    "Erreur de lien",
                    "Le lien de téléchargement n'est pas valide. Veuillez vérifier le lien et réessayer."
                )
                return
            
            # Créer une fenêtre d'attente
            self.wait_window = tk.Toplevel(self.root)
            self.wait_window.title("Ouverture du lien de téléchargement")
            self.wait_window.geometry("400x150")
            self.wait_window.configure(bg=self.bg_color)
            
            # Étiquette de texte
            label = tk.Label(
                self.wait_window, 
                text="Ouverture du lien de téléchargement dans le navigateur...\nVeuillez patienter un instant.",
                bg=self.bg_color,
                fg=self.text_color,
                font=("Arial", 10),
                justify=tk.CENTER
            )
            label.pack(pady=20)
            
            # Bouton Annuler
            cancel_btn = tk.Button(
                self.wait_window, 
                text="Annuler", 
                command=self.wait_window.destroy,
                bg=self.danger_color, 
                fg="white", 
                font=("Arial", 9, "bold"),
                relief=tk.FLAT, 
                bd=0, 
                padx=20, 
                pady=5
            )
            cancel_btn.pack(pady=10)
            
            # Ouvrir le lien dans un thread séparé pour éviter de bloquer l'interface
            threading.Thread(
                target=self._open_url_in_browser,
                args=(update_url,),
                daemon=True
            ).start()
            
        except Exception as e:
            logging.error(f"Erreur lors de l'ouverture du lien de mise à jour: {str(e)}")
            messagebox.showerror("Erreur", f"Échec de l'ouverture du lien de téléchargement: {str(e)}")
    
    def _open_url_in_browser(self, url):
        """Ouvrir l'URL dans le navigateur dans un thread séparé"""
        try:
            # Attendre un peu avant d'ouvrir l'URL
            time.sleep(1)
            
            # Ouvrir l'URL dans le navigateur par défaut
            webbrowser.open(url, new=2)  # new=2 ouvre dans un nouvel onglet si possible
            
            # Fermer la fenêtre d'attente après avoir ouvert l'URL
            if hasattr(self, 'wait_window') and self.wait_window.winfo_exists():
                self.root.after(0, self.wait_window.destroy)
            
            # Afficher un message de confirmation
            self.root.after(0, lambda: messagebox.showinfo(
                "Lien ouvert",
                "Le lien de téléchargement a été ouvert dans le navigateur.\n\nUne fois le téléchargement terminé, veuillez fermer l'application actuelle et lancer la nouvelle version."
            ))
            
            logging.info(f"Lien de mise à jour ouvert dans le navigateur: {url}")
            
        except Exception as e:
            error_message = f"Échec de l'ouverture de l'URL dans le navigateur: {str(e)}"
            logging.error(error_message)
            
            # Déterminer le message d'erreur en fonction du type d'exception
            if "browser" in str(e).lower():
                error_message = "Échec de l'ouverture du lien en raison d'un problème de navigateur. Veuillez vérifier les paramètres de votre navigateur et réessayer."
            elif "timeout" in str(e).lower():
                error_message = "Échec de l'ouverture du lien en raison d'un délai d'attente dépassé. Veuillez vérifier votre connexion Internet et réessayer."
            elif "connection" in str(e).lower():
                error_message = "Échec de l'ouverture du lien en raison d'un problème de connexion. Veuillez vérifier votre connexion Internet et réessayer."
            
            self.root.after(0, lambda: messagebox.showerror("Erreur lors de l'ouverture du lien", error_message))
            
            # Fermer la fenêtre d'attente en cas d'échec
            if hasattr(self, 'wait_window') and self.wait_window.winfo_exists():
                self.root.after(0, self.wait_window.destroy)
    
    def set_app_icon(self):
        """Définir l'icône de l'application"""
        try:
            if os.path.exists("logo.ico"):
                self.root.iconbitmap("logo.ico")
                logging.info("Icône de l'application définie avec succès")
        except Exception as e:
            logging.error(f"Erreur lors de la définition de l'icône de l'application: {str(e)}")
    
    def create_login_screen(self):
        """Créer l'écran de connexion"""
        # Effacer l'écran actuel
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Cadre de fond
        self.login_frame = tk.Frame(self.root, bg=self.bg_color)
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        
        # Cadre de connexion avec une couleur rose vif
        login_container = tk.Frame(self.login_frame, bg=self.pink_color, highlightthickness=0)
        login_container.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=500, height=400)
        
        # Message de bienvenue
        welcome_label = tk.Label(login_container, text="Hamza Ziadi", font=("Arial", 18, "bold"), 
                               bg=self.pink_color, fg=self.bg_color)  # Couleur de texte foncée pour être visible sur le fond rose
        welcome_label.pack(pady=(20, 5))
        
        # Description de l'application
        desc_label = tk.Label(login_container, text="Lecteur IPTV Professionnel avec lecteur interne", 
                             font=("Arial", 12), bg=self.pink_color, fg=self.bg_color)
        desc_label.pack(pady=(0, 20))
        
        # Titre de connexion
        title = tk.Label(login_container, text="Activation de l'abonnement", font=("Arial", 18, "bold"), 
                        bg=self.pink_color, fg=self.bg_color)
        title.pack(pady=(0, 20))
        
        # Champ de saisie du code d'activation
        code_frame = tk.Frame(login_container, bg=self.pink_color)
        code_frame.pack(pady=10, padx=40, fill=tk.X)
        
        code_label = tk.Label(code_frame, text="Code d'activation:", bg=self.pink_color, fg=self.bg_color, font=("Arial", 12))
        code_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.code_entry = tk.Entry(code_frame, font=("Arial", 14), bg="#fce7f3", fg=self.bg_color, 
                                  insertbackground=self.bg_color, relief=tk.FLAT, bd=0)
        self.code_entry.pack(fill=tk.X, pady=(0, 10), ipady=8)
        
        # Bouton d'activation
        activate_btn = tk.Button(login_container, text="Activer", command=self.activate_subscription, 
                               bg=self.accent_color, fg="white", font=("Arial", 12, "bold"),
                               relief=tk.FLAT, bd=0, padx=20, pady=10)
        activate_btn.pack(pady=10)
        
        # Bouton de rafraîchissement des données
        refresh_btn = tk.Button(login_container, text="Rafraîchir les données", command=self.refresh_data_from_firebase, 
                               bg=self.warning_color, fg="white", font=("Arial", 10),
                               relief=tk.FLAT, bd=0, padx=20, pady=5)
        refresh_btn.pack(pady=5)
        
        # Lier la touche Entrée au bouton d'activation
        self.code_entry.bind("<Return>", lambda event: self.activate_subscription())
        
        logging.info("Écran de connexion créé avec succès")
    
    def activate_subscription(self):
        """Activer l'abonnement en utilisant les informations du programme"""
        code = self.code_entry.get().strip()
        
        try:
            # Vérifier le code d'activation
            if code in self.subscription_codes:
                # Code correct
                self.subscription_active = True
                
                # Définir une date de fin d'abonnement à partir des informations du programme
                # Utiliser une date fixe pour l'exemple
                current_date = datetime.now()
                # Ajouter 30 jours à la date actuelle pour la fin d'abonnement
                end_date = current_date.replace(year=current_date.year + 1)  # Abonnement d'un an
                self.subscription_end_date = end_date.strftime("%Y-%m-%d %H:%M:%S")
                
                # Afficher un message de bienvenue (sans la date de fin)
                messagebox.showinfo("Activation réussie", "Bienvenue! Votre abonnement a été activé avec succès.")
                
                # Passer à l'écran principal
                self.create_main_screen()
                
                logging.info(f"Abonnement activé avec succès en utilisant le code: {code}")
            else:
                # Code incorrect
                messagebox.showerror("Erreur", "Le code d'activation est incorrect")
                self.code_entry.delete(0, tk.END)
                
                logging.warning(f"Tentative d'activation d'abonnement avec un code incorrect: {code}")
                
        except Exception as e:
            logging.error(f"Erreur lors de l'activation de l'abonnement: {str(e)}")
            messagebox.showerror("Erreur", f"Échec de la vérification du code d'activation: {str(e)}")
            self.code_entry.delete(0, tk.END)
    
    def create_main_screen(self):
        """Créer l'écran principal"""
        # Effacer l'écran actuel
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Cadre principal
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Cadre d'informations supérieur
        info_frame = tk.Frame(main_frame, bg=self.bg_color)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Titre de l'application
        title = tk.Label(info_frame, text="Lecteur IPTV avec lecteur interne", font=("Arial", 16, "bold"), 
                        bg=self.bg_color, fg=self.text_color)
        title.pack(side=tk.LEFT, padx=(10, 0))
        
        # Informations d'abonnement
        self.sub_info_label = tk.Label(info_frame, text=f"Abonnement actif jusqu'au: {self.subscription_end_date}", 
                           bg=self.bg_color, fg=self.success_color, font=("Arial", 10))
        self.sub_info_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Bouton de rafraîchissement des données
        refresh_btn = tk.Button(info_frame, text="Rafraîchir les données", command=self.refresh_data_from_firebase, 
                               bg=self.accent_color, fg="white", font=("Arial", 10),
                               relief=tk.FLAT, bd=0, padx=10, pady=5)
        refresh_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Bouton de déconnexion
        logout_btn = tk.Button(info_frame, text="Déconnexion", command=self.logout, 
                              bg=self.danger_color, fg="white", font=("Arial", 10),
                              relief=tk.FLAT, bd=0, padx=10, pady=5)
        logout_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Cadre de contenu principal
        content_frame = tk.Frame(main_frame, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Cadre des chaînes (côté gauche)
        left_frame = tk.Frame(content_frame, bg=self.bg_color, width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Cadre des catégories
        categories_frame = tk.LabelFrame(left_frame, text="Catégories", bg=self.card_color, 
                                        fg=self.text_color, font=("Arial", 12, "bold"))
        categories_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Tableau des catégories
        self.categories_tree = ttk.Treeview(categories_frame, columns=("id", "name"), show="headings", height=8)
        self.categories_tree.heading("id", text="Numéro")
        self.categories_tree.heading("name", text="Nom de la catégorie")
        self.categories_tree.column("id", width=50, anchor=tk.CENTER)
        self.categories_tree.column("name", width=300)
        self.categories_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.categories_tree.bind("<<TreeviewSelect>>", self.on_category_select)
        
        # Personnaliser l'apparence du tableau des catégories
        self.categories_tree.tag_configure("oddrow", background=self.light_card_color)
        self.categories_tree.tag_configure("evenrow", background=self.card_color)
        
        # Cadre des chaînes
        channels_frame = tk.LabelFrame(left_frame, text="Chaînes", bg=self.card_color, 
                                      fg=self.text_color, font=("Arial", 12, "bold"))
        channels_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tableau des chaînes
        self.channels_tree = ttk.Treeview(channels_frame, columns=("id", "name"), show="headings", height=10)
        self.channels_tree.heading("id", text="Numéro")
        self.channels_tree.heading("name", text="Nom de la chaîne")
        self.channels_tree.column("id", width=50, anchor=tk.CENTER)
        self.channels_tree.column("name", width=300)
        self.channels_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.channels_tree.bind("<<TreeviewSelect>>", self.on_channel_select)
        
        # Personnaliser l'apparence du tableau des chaînes
        self.channels_tree.tag_configure("oddrow", background=self.light_card_color)
        self.channels_tree.tag_configure("evenrow", background=self.card_color)
        
        # Cadre du lecteur et des informations (côté droit)
        right_frame = tk.Frame(content_frame, bg=self.bg_color, width=900)  # Largeur augmentée
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Cadre du lecteur
        player_frame = tk.LabelFrame(right_frame, text="Lecteur Interne", bg=self.card_color, 
                                    fg=self.text_color, font=("Arial", 12, "bold"))
        player_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Cadre vidéo - taille augmentée
        self.video_frame = tk.Frame(player_frame, bg="black", width=850, height=480)  # Taille augmentée
        self.video_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configuration du lecteur interne
        self.player = InternalPlayer(self.video_frame, self.update_status)
        
        # Boutons de contrôle du lecteur
        controls_frame = tk.Frame(player_frame, bg=self.card_color)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        play_btn = tk.Button(controls_frame, text="Lecture", command=self.play_channel, 
                            bg=self.success_color, fg="white", font=("Arial", 10),
                            relief=tk.FLAT, bd=0, padx=10, pady=5)
        play_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        stop_btn = tk.Button(controls_frame, text="Arrêter", command=self.stop_player, 
                            bg=self.danger_color, fg="white", font=("Arial", 10),
                            relief=tk.FLAT, bd=0, padx=10, pady=5)
        stop_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        fullscreen_btn = tk.Button(controls_frame, text="Lecteur séparé", command=self.open_secondary_player, 
                                  bg=self.purple_color, fg="white", font=("Arial", 10),
                                  relief=tk.FLAT, bd=0, padx=10, pady=5)
        fullscreen_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        mute_btn = tk.Button(controls_frame, text="Muet/Activer", command=self.toggle_mute, 
                            bg=self.warning_color, fg="white", font=("Arial", 10),
                            relief=tk.FLAT, bd=0, padx=10, pady=5)
        mute_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        volume_label = tk.Label(controls_frame, text="Volume:", bg=self.card_color, fg=self.text_color, font=("Arial", 10))
        volume_label.pack(side=tk.LEFT, padx=(20, 5))
        
        self.volume_slider = tk.Scale(controls_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                     bg=self.card_color, fg=self.text_color, 
                                     highlightbackground=self.card_color,
                                     command=self.set_volume)
        self.volume_slider.set(80)
        self.volume_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Cadre d'informations d'abonnement - horizontal sous le lecteur avec espace
        subscription_info_frame = tk.LabelFrame(right_frame, text="Informations d'Abonnement", bg=self.card_color, 
                                               fg=self.text_color, font=("Arial", 12, "bold"))
        subscription_info_frame.pack(fill=tk.X, pady=(10, 0), ipady=10)  # Espace ajouté et hauteur augmentée
        
        # Tableau d'informations d'abonnement horizontal - taille augmentée
        self.subscription_info_tree = ttk.Treeview(subscription_info_frame, columns=("status", "max_connections", "exp_date", "created_at"), show="headings", height=2)
        self.subscription_info_tree.heading("status", text="Statut")
        self.subscription_info_tree.heading("max_connections", text="Connexions Max")
        self.subscription_info_tree.heading("exp_date", text="Date de Fin")
        self.subscription_info_tree.heading("created_at", text="Date de Création")
        self.subscription_info_tree.column("status", width=150, anchor=tk.CENTER)  # Largeur augmentée
        self.subscription_info_tree.column("max_connections", width=150, anchor=tk.CENTER)  # Largeur augmentée
        self.subscription_info_tree.column("exp_date", width=250, anchor=tk.CENTER)  # Largeur augmentée
        self.subscription_info_tree.column("created_at", width=250, anchor=tk.CENTER)  # Largeur augmentée
        self.subscription_info_tree.pack(fill=tk.X, padx=5, pady=5)
        
        # Personnaliser l'apparence du tableau d'informations d'abonnement
        self.subscription_info_tree.tag_configure("oddrow", background=self.light_card_color)
        self.subscription_info_tree.tag_configure("evenrow", background=self.card_color)
        
        # Remplir les informations d'abonnement
        self.update_subscription_info()
        
        # Barre de statut
        self.status_var = tk.StringVar()
        self.status_var.set("Chargement des données...")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bg=self.card_color, 
                             fg=self.text_color, anchor=tk.W, padx=10, font=("Arial", 9))
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Charger les données
        self.load_data()
        
        logging.info("Écran principal créé avec succès")
    
    def update_subscription_info(self):
        """Mettre à jour les informations d'abonnement"""
        try:
            # Effacer les informations existantes
            self.subscription_info_tree.delete(*self.subscription_info_tree.get_children())
            
            # Préparer les valeurs
            status = "Actif" if self.subscription_active else "Inactif"
            max_connections = getattr(self, 'user_max_connections', "Inconnu")
            exp_date = getattr(self, 'user_exp_date', "Inconnu")
            created_at = getattr(self, 'user_created_at', "Inconnu")
            
            # Ajouter une seule ligne avec les quatre valeurs
            self.subscription_info_tree.insert("", tk.END, values=(status, max_connections, exp_date, created_at), 
                                            tags=("evenrow",))
            
            logging.info("Informations d'abonnement mises à jour avec succès")
            
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour des informations d'abonnement: {str(e)}")
    
    def open_secondary_player(self):
        """Ouvrir un deuxième lecteur dans une fenêtre séparée"""
        # Si le deuxième lecteur est déjà ouvert, le fermer
        if self.secondary_player_window is not None:
            self.secondary_player_window.destroy()
        
        # Créer la fenêtre du deuxième lecteur
        self.secondary_player_window = tk.Toplevel(self.root)
        self.secondary_player_window.title("Lecteur IPTV Séparé")
        self.secondary_player_window.geometry("1000x700")  # Taille augmentée
        self.secondary_player_window.configure(bg=self.bg_color)
        
        # Définir l'icône pour le deuxième lecteur
        self.set_secondary_player_icon()
        
        # Cadre vidéo dans le deuxième lecteur
        secondary_video_frame = tk.Frame(self.secondary_player_window, bg="black")
        secondary_video_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configuration du deuxième lecteur
        self.secondary_player = InternalPlayer(secondary_video_frame, self.update_secondary_status)
        
        # Boutons de contrôle dans le deuxième lecteur
        secondary_controls_frame = tk.Frame(self.secondary_player_window, bg=self.card_color)
        secondary_controls_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Bouton de lecture dans le deuxième lecteur
        secondary_play_btn = tk.Button(secondary_controls_frame, text="Lecture", 
                                      command=self.play_in_secondary_player,
                                      bg=self.success_color, fg="white", font=("Arial", 10),
                                      relief=tk.FLAT, bd=0, padx=10, pady=5)
        secondary_play_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Bouton d'arrêt dans le deuxième lecteur
        secondary_stop_btn = tk.Button(secondary_controls_frame, text="Arrêter", 
                                      command=self.stop_secondary_player,
                                      bg=self.danger_color, fg="white", font=("Arial", 10),
                                      relief=tk.FLAT, bd=0, padx=10, pady=5)
        secondary_stop_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Bouton de plein écran dans le deuxième lecteur
        secondary_fullscreen_btn = tk.Button(secondary_controls_frame, text="Plein Écran", 
                                           command=self.toggle_secondary_fullscreen,
                                           bg=self.purple_color, fg="white", font=("Arial", 10),
                                           relief=tk.FLAT, bd=0, padx=10, pady=5)
        secondary_fullscreen_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Bouton de muet dans le deuxième lecteur
        secondary_mute_btn = tk.Button(secondary_controls_frame, text="Muet/Activer", 
                                      command=self.toggle_secondary_mute,
                                      bg=self.warning_color, fg="white", font=("Arial", 10),
                                      relief=tk.FLAT, bd=0, padx=10, pady=5)
        secondary_mute_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Barre de volume dans le deuxième lecteur
        secondary_volume_label = tk.Label(secondary_controls_frame, text="Volume:", bg=self.card_color, fg=self.text_color, font=("Arial", 10))
        secondary_volume_label.pack(side=tk.LEFT, padx=(20, 5))
        
        secondary_volume_slider = tk.Scale(secondary_controls_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                         bg=self.card_color, fg=self.text_color, 
                                         highlightbackground=self.card_color,
                                         command=self.set_secondary_volume)
        secondary_volume_slider.set(80)
        secondary_volume_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Barre de statut dans le deuxième lecteur
        self.secondary_status_var = tk.StringVar()
        self.secondary_status_var.set("Prêt")
        secondary_status_bar = tk.Label(self.secondary_player_window, textvariable=self.secondary_status_var, 
                                        bg=self.card_color, fg=self.text_color, anchor=tk.W, padx=10, font=("Arial", 9))
        secondary_status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Fermer le deuxième lecteur lors de la fermeture de la fenêtre
        self.secondary_player_window.protocol("WM_DELETE_WINDOW", self.close_secondary_player)
        
        # Lier la touche Échap pour quitter le plein écran dans le deuxième lecteur
        self.secondary_player_window.bind('<Escape>', lambda e: self.toggle_secondary_fullscreen())
        
        logging.info("Fenêtre du deuxième lecteur créée avec succès")
    
    def set_secondary_player_icon(self):
        """Définir l'icône pour le deuxième lecteur"""
        try:
            if os.path.exists("logo.ico"):
                self.secondary_player_window.iconbitmap("logo.ico")
                logging.info("Icône du deuxième lecteur définie avec succès")
        except Exception as e:
            logging.error(f"Erreur lors de la définition de l'icône du deuxième lecteur: {str(e)}")
    
    def play_in_secondary_player(self):
        """Lire la chaîne dans le deuxième lecteur"""
        if self.secondary_player is None:
            logging.warning("Tentative de lecture d'une chaîne alors que le deuxième lecteur n'est pas disponible")
            messagebox.showwarning("Attention", "Le deuxième lecteur n'est pas disponible")
            return
        
        selected_items = self.channels_tree.selection()
        if not selected_items:
            logging.warning("Tentative de lecture d'une chaîne sans sélectionner de chaîne")
            messagebox.showwarning("Attention", "Veuillez sélectionner une chaîne d'abord")
            return
        
        # Obtenir la chaîne sélectionnée
        selected_item = self.channels_tree.item(selected_items[0])
        channel_id = selected_item["values"][0]
        channel_name = selected_item["values"][1]
        
        # Créer l'URL de lecture
        stream_url = f"{self.base_url}/{self.username}/{self.password}/{channel_id}"
        
        # Lire la chaîne dans le deuxième lecteur
        self.secondary_player.play(stream_url, channel_name)
    
    def stop_secondary_player(self):
        """Arrêter le deuxième lecteur"""
        if self.secondary_player is not None:
            self.secondary_player.stop()
    
    def toggle_secondary_fullscreen(self):
        """Basculer le mode plein écran dans le deuxième lecteur"""
        if self.secondary_player_window is None:
            return
            
        try:
            if self.secondary_player_window.attributes('-fullscreen'):
                # Retourner au mode normal
                self.secondary_player_window.attributes('-fullscreen', False)
                self.secondary_status_var.set("Sortie du mode plein écran")
                logging.info("Sortie du mode plein écran dans le deuxième lecteur")
            else:
                # Entrer en mode plein écran
                self.secondary_player_window.attributes('-fullscreen', True)
                self.secondary_status_var.set("Entrée en mode plein écran")
                logging.info("Entrée en mode plein écran dans le deuxième lecteur")
        except Exception as e:
            logging.error(f"Erreur lors du basculement du mode plein écran dans le deuxième lecteur: {str(e)}")
    
    def set_secondary_volume(self, volume):
        """Régler le volume dans le deuxième lecteur"""
        if self.secondary_player is not None:
            self.secondary_player.set_volume(int(volume))
    
    def toggle_secondary_mute(self):
        """Basculer le mode muet dans le deuxième lecteur"""
        if self.secondary_player is not None:
            self.secondary_player.toggle_mute()
    
    def close_secondary_player(self):
        """Fermer le deuxième lecteur"""
        if self.secondary_player is not None:
            self.secondary_player.stop()
            self.secondary_player = None
        
        if self.secondary_player_window is not None:
            self.secondary_player_window.destroy()
            self.secondary_player_window = None
    
    def logout(self):
        """Se déconnecter et retourner à l'écran de connexion"""
        # Fermer le deuxième lecteur s'il est ouvert
        self.close_secondary_player()
        
        self.subscription_active = False
        self.subscription_end_date = None
        self.create_login_screen()
        
        logging.info("Déconnexion de l'utilisateur réussie")
    
    def load_data(self):
        """Charger les données de l'utilisateur, des chaînes et des catégories"""
        self.status_var.set("Chargement des données...")
        self.root.update()
        
        # Démarrer le processus de chargement dans un thread séparé
        threading.Thread(target=self._load_data_thread, daemon=True).start()
    
    def _load_data_thread(self):
        """Charger les données dans un thread séparé"""
        try:
            # Obtenir les informations de l'utilisateur
            logging.info("Chargement des informations de l'utilisateur...")
            user_info_response = requests.get(f"{self.api_url}&action=user", timeout=10)
            user_info = user_info_response.json()
            
            # Obtenir les informations du serveur
            logging.info("Chargement des informations du serveur...")
            server_info_response = requests.get(f"{self.api_url}&action=server_info", timeout=10)
            server_info = server_info_response.json()
            
            # Obtenir la liste des catégories
            logging.info("Chargement de la liste des catégories...")
            categories_response = requests.get(f"{self.api_url}&action=get_live_categories", timeout=10)
            self.categories = categories_response.json()
            
            # Mettre à jour l'interface utilisateur dans le thread principal
            self.root.after(0, self.update_ui, user_info, server_info)
            
            logging.info("Données chargées avec succès")
            
        except Exception as e:
            logging.error(f"Erreur lors du chargement des données: {str(e)}")
            self.root.after(0, self.show_error, f"Erreur lors du chargement des données: {str(e)}")
    
    def update_ui(self, user_info, server_info):
        """Mettre à jour l'interface utilisateur après le chargement des données"""
        try:
            # Informations de l'utilisateur
            if "user_info" in user_info:
                ui = user_info["user_info"]
                
                # Extraire les informations de l'API
                self.user_status = ui.get("status", "Inconnu")
                self.user_max_connections = ui.get("max_connections", "Inconnu")
                
                # Date de fin d'abonnement (exp_date)
                exp_date_timestamp = ui.get("exp_date", "0")
                if exp_date_timestamp != "0":
                    self.user_exp_date = datetime.fromtimestamp(int(exp_date_timestamp)).strftime("%Y-%m-%d %H:%M:%S")
                    # Mettre à jour la date de fin d'abonnement pour l'affichage dans le bandeau supérieur
                    self.subscription_end_date = self.user_exp_date
                else:
                    self.user_exp_date = "Illimité"
                    self.subscription_end_date = "Illimité"
                
                # Date de création d'abonnement (created_at)
                created_at_timestamp = ui.get("created_at", "0")
                if created_at_timestamp != "0":
                    self.user_created_at = datetime.fromtimestamp(int(created_at_timestamp)).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    self.user_created_at = "Inconnu"
            
            # Informations du serveur
            if "server_info" in server_info:
                si = server_info["server_info"]
                
                # Protocole
                protocol = si.get("server_protocol", "Inconnu")
            
            # Mettre à jour la liste des catégories
            self.categories_tree.delete(*self.categories_tree.get_children())
            for i, category in enumerate(self.categories):
                self.categories_tree.insert("", tk.END, values=(category.get("category_id", ""), category.get("category_name", "")), 
                                          tags=("evenrow" if i % 2 == 0 else "oddrow",))
            
            # Mettre à jour les informations d'abonnement
            self.update_subscription_info()
            
            # Mettre à jour le label d'abonnement dans le bandeau supérieur
            self.sub_info_label.config(text=f"Abonnement actif jusqu'au: {self.subscription_end_date}")
            
            self.status_var.set("Données chargées avec succès")
            
            logging.info("Interface utilisateur mise à jour avec succès")
            
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour de l'interface utilisateur: {str(e)}")
            self.show_error(f"Erreur lors de la mise à jour de l'interface: {str(e)}")
    
    def on_category_select(self, event):
        """Lors de la sélection d'une catégorie"""
        selected_items = self.categories_tree.selection()
        if not selected_items:
            return
        
        # Obtenir la catégorie sélectionnée
        selected_item = self.categories_tree.item(selected_items[0])
        category_id = selected_item["values"][0]
        self.selected_category = category_id
        
        # Charger les chaînes de cette catégorie
        self.status_var.set("Chargement des chaînes de la catégorie...")
        self.root.update()
        
        # Démarrer le processus de chargement dans un thread séparé
        threading.Thread(target=self._load_channels_thread, args=(category_id,), daemon=True).start()
    
    def _load_channels_thread(self, category_id):
        """Charger les chaînes de la catégorie dans un thread séparé"""
        try:
            # Obtenir les chaînes de la catégorie
            logging.info(f"Chargement des chaînes de la catégorie: {category_id}")
            channels_response = requests.get(f"{self.api_url}&action=get_live_streams&category_id={category_id}", timeout=10)
            self.channels = channels_response.json()
            
            # Mettre à jour l'interface utilisateur dans le thread principal
            self.root.after(0, self.update_channels_list)
            
            logging.info(f"Chaînes de la catégorie {category_id} chargées avec succès")
            
        except Exception as e:
            logging.error(f"Erreur lors du chargement des chaînes de la catégorie: {str(e)}")
            self.root.after(0, self.show_error, f"Erreur lors du chargement des chaînes: {str(e)}")
    
    def update_channels_list(self):
        """Mettre à jour la liste des chaînes"""
        try:
            # Mettre à jour la liste des chaînes
            self.channels_tree.delete(*self.channels_tree.get_children())
            for i, channel in enumerate(self.channels):
                self.channels_tree.insert("", tk.END, values=(channel.get("stream_id", ""), channel.get("name", "")), 
                                       tags=("evenrow" if i % 2 == 0 else "oddrow",))
            
            self.status_var.set(f"{len(self.channels)} chaînes chargées")
            
            logging.info(f"Liste des chaînes mise à jour avec succès, nombre de chaînes: {len(self.channels)}")
            
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour de la liste des chaînes: {str(e)}")
            self.show_error(f"Erreur lors de la mise à jour de la liste des chaînes: {str(e)}")
    
    def on_channel_select(self, event):
        """Lors de la sélection d'une chaîne - la lire directement"""
        selected_items = self.channels_tree.selection()
        if not selected_items:
            return
        
        # Obtenir la chaîne sélectionnée
        selected_item = self.channels_tree.item(selected_items[0])
        channel_id = selected_item["values"][0]
        channel_name = selected_item["values"][1]
        
        # Rechercher la chaîne dans la liste
        selected_channel = None
        for channel in self.channels:
            if str(channel.get("stream_id", "")) == str(channel_id):
                selected_channel = channel
                break
        
        if selected_channel:
            self.selected_channel = selected_channel
            self.status_var.set(f"Chaîne sélectionnée: {channel_name}")
            
            # Lire la chaîne directement
            self.play_selected_channel(channel_id, channel_name)
            
            # Enregistrer la sélection de la chaîne avec un traitement spécial pour les caractères arabes
            try:
                logging.info(f"Chaîne sélectionnée: {channel_name}")
            except UnicodeEncodeError:
                # Si l'enregistrement du message échoue en raison de l'encodage des caractères arabes
                logging.info(f"Chaîne sélectionnée: {channel_name.encode('utf-8', errors='replace').decode('utf-8')}")
    
    def play_selected_channel(self, channel_id, channel_name):
        """Lire une chaîne spécifiée directement"""
        # Créer l'URL de lecture
        stream_url = f"{self.base_url}/{self.username}/{self.password}/{channel_id}"
        
        # Enregistrer l'URL pour le débogage
        logging.info(f"Tentative de lecture de la chaîne: {channel_name} depuis l'URL: {stream_url}")
        
        # Lire la chaîne
        try:
            # Vérifier la validité de l'URL
            if not self.is_valid_url(stream_url):
                raise ValueError("URL de streaming non valide")
            
            # Lire la chaîne
            self.player.play(stream_url, channel_name)
            
            logging.info(f"Démarrage de la lecture de la chaîne: {channel_name}")
        except Exception as e:
            logging.error(f"Erreur lors de la lecture de la chaîne: {str(e)}")
            messagebox.showerror("Erreur de lecture", f"Échec de la lecture de la chaîne: {str(e)}")
            self.status_var.set(f"Erreur lors de la lecture de la chaîne: {channel_name}")
    
    def play_channel(self):
        """Lire la chaîne sélectionnée"""
        selected_items = self.channels_tree.selection()
        if not selected_items:
            logging.warning("Tentative de lecture d'une chaîne sans sélectionner de chaîne")
            messagebox.showwarning("Attention", "Veuillez sélectionner une chaîne d'abord")
            return
        
        # Obtenir la chaîne sélectionnée
        selected_item = self.channels_tree.item(selected_items[0])
        channel_id = selected_item["values"][0]
        channel_name = selected_item["values"][1]
        
        # Lire la chaîne
        self.play_selected_channel(channel_id, channel_name)
    
    def stop_player(self):
        """Arrêter le lecteur"""
        if self.player is not None:
            self.player.stop()
    
    def set_volume(self, volume):
        """Régler le volume"""
        if self.player is not None:
            self.player.set_volume(int(volume))
    
    def toggle_mute(self):
        """Basculer le mode muet"""
        if self.player is not None:
            self.player.toggle_mute()
    
    def update_status(self, status):
        """Mettre à jour la barre de statut"""
        self.status_var.set(status)
    
    def update_secondary_status(self, status):
        """Mettre à jour la barre de statut dans le deuxième lecteur"""
        if self.secondary_status_var:
            self.secondary_status_var.set(status)
    
    def show_error(self, message):
        """Afficher un message d'erreur"""
        logging.error(f"Affichage d'un message d'erreur: {message}")
        messagebox.showerror("Erreur", message)
        self.status_var.set(f"Erreur: {message}")

def setup_styles():
    """Configurer les styles de l'interface utilisateur"""
    style = ttk.Style()
    style.theme_use('clam')
    
    # Personnaliser les couleurs de l'application
    style.configure("Treeview", background=CARD_COLOR, foreground=TEXT_COLOR, fieldbackground=CARD_COLOR, font=("Arial", 10))
    style.configure("Treeview.Heading", background=CARD_COLOR, foreground=TEXT_COLOR, font=("Arial", 11, "bold"))
    style.map("Treeview", background=[('selected', ACCENT_COLOR)])

if __name__ == "__main__":
    try:
        root = tk.Tk()
        
        # Configurer le style de l'application
        setup_styles()
        
        app = IPTVPlayerApp(root)
        root.mainloop()
        
    except Exception as e:
        logging.critical(f"Erreur critique lors de l'exécution de l'application: {str(e)}")
        print(f"Erreur critique lors de l'exécution de l'application: {str(e)}")
        sys.exit(1)
