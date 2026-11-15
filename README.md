# Rayman (Saturn, Europe) — patch 60 Hz / 240 lignes

Patch pour **Rayman sur Sega Saturn, version européenne** (En/Fr/De), qui fait tourner le jeu en
**60 Hz** avec un affichage de **240 lignes**, en français.

Aucune donnée du jeu n'est fournie : il faut sa propre image disque.

## Ce que fait le patch

- **60 Hz, 240 lignes** (au lieu de 50 Hz, 256 lignes), région du disque passée en NTSC (USA/Canada, Brésil, Taïwan/Philippines).
- **Vitesse de jeu corrigée** : la compensation 50 Hz de la version PAL est retirée. Vitesse de Rayman et
  minuteries vérifiées identiques à la version US (2 px/image en marche).
- **Cadrage en jeu** : les niveaux PAL ont 32 lignes de plus en haut que les niveaux US. Le patch
  affiche la vue US **plus 16 lignes en haut**, avec le même bas : on ne perd rien par rapport à la version US.
  L'interface (vies, tings) reste à sa place.
- **Écrans fixes** (titre, menus, carte, images) centrés : contenu PAL utile entièrement visible.
- **Français forcé** (le jeu prenait la langue du BIOS), **« APPUYEZ SUR START »** au lieu de « PRESS START BUTTON ».
- Écran titre : « © Ubi Soft 1995 » descendu de 5 lignes pour ne plus toucher le haut de l'écran.

## Appliquer le patch

Fichier source attendu : **`Rayman (Europe) (En,Fr,De) (1S) (Track 01).bin`** (dump Redump)

| | |
|---|---|
| Taille | 152 482 512 octets |
| CRC32 | `07997b9c` |
| MD5 | `88bb0bfd24405d149c621fc8def64775` |

1. Télécharger `rayman-saturn-fr-60hz-track01.bps` depuis la page *Releases*.
2. L'appliquer sur la piste 1 avec [Floating IPS](https://github.com/Alcaro/Flips), [ROM Patcher JS](https://www.marcrobledo.com/RomPatcher.js/)
   ou `python tools/mkbps.py apply <piste01.bin> <patch.bps> <sortie.bin>`.
3. Remplacer la piste 1 par le fichier patché (même nom), garder les pistes audio et le `.cue` d'origine.

MD5 de la piste 1 patchée : `e71afff022bb092ba844aaaa0b000cee`.

**SSF** : SSF lit mal les images en plusieurs fichiers. Fusionner les pistes en un seul `.bin` :
`python tools/merge.py "<image>.cue" <dossier_sortie> "Rayman FR 60Hz"`.

## Limites connues

- « DEMO PLAY » reste en anglais (texte codé en dur dans le jeu).
- Images de chargement : centrées sous Mednafen ; un écart d'affichage a été signalé sous SSF, non résolu.
- Testé sous Mednafen et SSF uniquement, pas sur une vraie console.

## Reconstruire depuis les sources

`tools/build.sh` reconstruit l'image patchée à partir de l'image d'origine. Il faut en plus :
- l'exécutable principal du jeu (fichier `0` du disque) dans `tools/data/fr/0` (extraction : `python tools/iso.py <piste01.bin> <dossier>`) ;
- la piste de données de la version US (pour les secteurs de région) ;
- Python 3 avec `numpy` et `pillow`.

Principaux fichiers :
- `make_patch.py` : patchs de l'exécutable (affichage, vitesse, centrage, interface, langue) ;
- `sh2asm.py` : mini-assembleur SH-2 pour les routines ajoutées ;
- `region_ntsc.py`, `title_bg.py` : région du disque, image de l'écran titre ;
- `mkbps.py` : création/application du patch BPS.
