# Rayman (Saturn, Europe) — patch 60 Hz / 240 lignes + intro PS1 en 320×200

Patch pour **Rayman sur Sega Saturn, version européenne** (En/Fr/De), qui fait tourner le jeu en
**60 Hz** avec un affichage de **240 lignes**, en français, et remplace la cinématique d'introduction
par celle de la **version PlayStation, en 320×200 stéréo**.

Aucune donnée du jeu n'est fournie dans ce dépôt : il faut sa propre image disque.

## Ce que fait le patch

### Affichage et jeu
- **60 Hz, 240 lignes** (au lieu de 50 Hz, 256 lignes), région du disque passée en NTSC (USA/Canada, Brésil, Taïwan/Philippines).
- **Vitesse de jeu corrigée** : la compensation 50 Hz de la version PAL est retirée. Vitesse de Rayman et
  minuteries vérifiées identiques à la version US (2 px/image en marche).
- **Cadrage en jeu** : les niveaux PAL ont 32 lignes de plus en haut que les niveaux US. Le patch
  affiche la vue US **plus 16 lignes en haut**, avec le même bas : on ne perd rien par rapport à la version US.
  L'interface (vies, tings) reste à sa place.
- **Écrans fixes** (titre, menus, carte, images) centrés : contenu PAL utile entièrement visible.
- **Français forcé** (le jeu prenait la langue du BIOS), **« APPUYEZ SUR START »** au lieu de « PRESS START BUTTON ».
- Écran titre : « © Ubi Soft 1995 » descendu de 5 lignes pour ne plus toucher le haut de l'écran.

### Cinématique d'introduction (v1.1)
La vidéo d'intro (avant la carte, en début de partie) est remplacée par celle de la version PS1 :

| | Saturn d'origine | **Patch v1.1** |
|---|---|---|
| Résolution | 256×160 | **320×200** (résolution native PS1) |
| Images/s | 15 | **16,67** (cadence exacte de la PS1) |
| Son | mono 44,1 kHz | **stéréo 22,05 kHz** (vraie stéréo de la PS1) |
| Débit | 246 Ko/s | 252 Ko/s (lecteur CD 2x : ~300 Ko/s) |

Contraintes respectées pour le lecteur vidéo du jeu (`CPK.BIN`, Cinepak Sega) : conteneur Sega FILM 1.06
organisé comme l'original, **une seule bande Cinepak par image** (le décodeur Sega n'en accepte pas plus),
blocs alignés sur 4 octets. La vidéo occupe aussi la place des vidéos anglaises, inutilisées puisque le
jeu est forcé en français ; leurs entrées pointent vers les vidéos françaises.

Qualité par rapport à la PS1 : même résolution et même cadence ; Cinepak (512 blocs de couleurs par image)
adoucit les détails fins et marque un peu les dégradés (PSNR ≈ 30 dB sur les images non noires).

## Appliquer le patch

Fichier source attendu : **`Rayman (Europe) (En,Fr,De) (1S) (Track 01).bin`** (dump Redump)

| | |
|---|---|
| Taille | 152 482 512 octets |
| CRC32 | `07997b9c` |
| MD5 | `88bb0bfd24405d149c621fc8def64775` |

1. Télécharger le patch `.bps` depuis la page *Releases* (`v1.1` : avec la nouvelle intro ; `v1.0` : sans).
2. L'appliquer sur la piste 1 avec [Floating IPS](https://github.com/Alcaro/Flips), [ROM Patcher JS](https://www.marcrobledo.com/RomPatcher.js/)
   ou `python tools/mkbps.py apply <piste01.bin> <patch.bps> <sortie.bin>`.
3. Remplacer la piste 1 par le fichier patché (même nom), garder les pistes audio et le `.cue` d'origine.

MD5 de la piste 1 patchée : v1.1 `d488803bb5a9d553a2d262d5e5880f0d` — v1.0 `e71afff022bb092ba844aaaa0b000cee`.

**SSF** : SSF lit mal les images en plusieurs fichiers. Fusionner les pistes en un seul `.bin` :
`python tools/merge.py "<image>.cue" <dossier_sortie> "Rayman FR 60Hz"`.

## Limites connues

- « DEMO PLAY » reste en anglais (texte codé en dur dans le jeu).
- Images de chargement : centrées sous Mednafen ; un écart d'affichage a été signalé sous SSF, non résolu.
- Testé sous Mednafen (et SSF pour la partie 60 Hz), pas sur une vraie console. La vidéo v1.1 a été validée sous Mednafen.

## Reconstruire depuis les sources

`tools/build.sh` reconstruit l'image patchée à partir de l'image d'origine. Il faut en plus :
- l'exécutable principal du jeu (fichier `0` du disque) dans `tools/data/fr/0` (extraction : `python tools/iso.py <piste01.bin> <dossier>`) ;
- la piste de données de la version US (pour les secteurs de région) ;
- pour la vidéo : `sh tools/make_video.sh "<piste 01 du disque PS1 Rayman (Europe)>"` (ffmpeg requis), qui produit
  `video/AFR_final.cpk`, inséré automatiquement par `build.sh` ;
- Python 3 avec `numpy` et `pillow`.

Principaux fichiers :
- `make_patch.py` : patchs de l'exécutable (affichage, vitesse, centrage, interface, langue) ;
- `sh2asm.py` : mini-assembleur SH-2 pour les routines ajoutées ;
- `region_ntsc.py`, `title_bg.py` : région du disque, image de l'écran titre ;
- `mkfilm.py`, `cvidfix.py` : conteneur Sega FILM et compatibilité Cinepak avec le lecteur Saturn ;
- `replace_file.py` : remplacement d'un fichier dans l'image disque (EDC/ECC, répertoire ISO) ;
- `mkbps.py` : création/application du patch BPS.
