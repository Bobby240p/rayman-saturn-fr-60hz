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

- **Logo Ubi Soft raccourci (v1.2)** : le jeu garde le logo à l'écran jusqu'à la fin de la piste audio 16 ;
  sa longue traîne presque inaudible est coupée (piste ramenée à 9,6 s avec fondu). On arrive sur l'écran
  titre environ 2,5 s plus tôt que sur la version PAL d'origine.

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

## Appliquer le patch (v1.2)

La release v1.2 contient **deux patchs BPS**, à appliquer sur les pistes du dump Redump
`Rayman (Europe) (En,Fr,De) (1S)` :

| Patch | Fichier source | CRC32 source | MD5 résultat |
|---|---|---|---|
| `...-v1.2-track01.bps` | `(Track 01).bin` (152 482 512 octets) | `07997b9c` | `d488803bb5a9d553a2d262d5e5880f0d` |
| `...-v1.2-track16.bps` | `(Track 16).bin` (1 999 200 octets) | `18abdccd` | `9edaccf377685aef55030aac2c941fd7` |

1. Appliquer chaque patch sur sa piste avec [Floating IPS](https://github.com/Alcaro/Flips),
   [ROM Patcher JS](https://www.marcrobledo.com/RomPatcher.js/) ou `python tools/mkbps.py apply <piste.bin> <patch.bps> <sortie.bin>`.
2. Remplacer les pistes 01 et 16 par les fichiers patchés (mêmes noms), garder les autres pistes et le `.cue` d'origine.

**Console avec Fenrir** : garder ce format Redump (un fichier par piste, `.cue` d'origine). Une image fusionnée en
un seul `.bin` reste bloquée sur l'écran de chargement de Fenrir.

**Émulateur SSF** : à l'inverse, SSF lit mal les images en plusieurs fichiers. Les fusionner en un seul `.bin` :
`python tools/merge.py "<image>.cue" <dossier_sortie> "Rayman FR 60Hz"`.

## Vérification « plus rien en 50 Hz »

- **Gameplay** : la démo Band Land rejouée dans la version US et dans la version patchée reste synchronisée du début à la fin
  (mêmes positions, même compteur de tings aux mêmes instants) ; vitesse de marche et compteurs internes identiques à l'US.
- **Code** : toutes les vitesses et minuteries ont les valeurs US ; les constantes restées en version PAL sont de la mise en page
  (hauteur d'écran, lignes de texte, positions), compensée par le centrage et le cadrage.
- **Son** : les musiques sont des pistes CD lues à vitesse fixe, de même durée que sur le disque US ; les banques de bruitages
  sont identiques à l'US à 2 octets près (un volume et un réglage de mixage, sans lien avec la vitesse).

## Limites connues

- « DEMO PLAY » reste en anglais (texte codé en dur dans le jeu).
- Images de chargement : centrées sous Mednafen ; un écart d'affichage a été signalé sous SSF, non résolu.
- Testé sous Mednafen et SSF, et sur Saturn réelle (Fenrir, format Redump multi-fichiers).

## Reconstruire depuis les sources

`tools/build.sh` reconstruit l'image patchée à partir de l'image d'origine. Il faut en plus :
- l'exécutable principal du jeu (fichier `0` du disque) dans `tools/data/fr/0` (extraction : `python tools/iso.py <piste01.bin> <dossier>`) ;
- la piste de données de la version US (pour les secteurs de région) ;
- pour la piste 16 : `python tools/trim_track.py "<(Track 16).bin>" audio/Track16_court.bin 9.6 0.4` (utilisée par `build.sh`) ;
- pour la vidéo : `sh tools/make_video.sh "<piste 01 du disque PS1 Rayman (Europe)>"` (ffmpeg requis), qui produit
  `video/AFR_final.cpk`, inséré automatiquement par `build.sh` ;
- Python 3 avec `numpy` et `pillow`.

Principaux fichiers :
- `make_patch.py` : patchs de l'exécutable (affichage, vitesse, centrage, interface, langue) ;
- `sh2asm.py` : mini-assembleur SH-2 pour les routines ajoutées ;
- `region_ntsc.py`, `title_bg.py` : région du disque, image de l'écran titre ;
- `mkfilm.py`, `cvidfix.py` : conteneur Sega FILM et compatibilité Cinepak avec le lecteur Saturn ;
- `replace_file.py` : remplacement d'un fichier dans l'image disque (EDC/ECC, répertoire ISO) ;
- `trim_track.py` : raccourcissement de la piste audio du logo ;
- `mkbps.py` : création/application des patchs BPS.
