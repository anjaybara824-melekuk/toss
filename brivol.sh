#!/usr/bin/env bash

# Sembunyikan kursor dan bersihkan layar saat keluar
trap "tput cnorm; clear; exit" EXIT
tput civis

while true; do
    # Ambil data volume & kecerahan
    VOL=$(amixer sget Master | grep -Po '\[\d+%\]' | head -1 | tr -d '[]%')
    BRIGHT=$(brightnessctl info | grep -Po '\d+(?=%)' | head -1)
    
    # Skala bar (tinggi 20 baris)
    V_BAR=$((VOL / 5))
    B_BAR=$((BRIGHT / 5))
    
    clear
    COLS=$(tput cols)
    
    # Fungsi teks tengah
    center() {
        printf "%*s\n" $(((${#1} + COLS) / 2)) "$1"
    }

    echo ""
    center "TOSS BRIVOL CONTROL"
    center "==================="
    echo ""

    # Top Border (Tutup Atas)
    printf "%*s ┌───┐   ┌───┐\n" $((COLS/2 - 7)) ""

    # Isi Bar Vertikal
    for ((i=20; i>=1; i--)); do
        if [ "$i" -le "$V_BAR" ]; then v_char="█"; else v_char=" "; fi
        if [ "$i" -le "$B_BAR" ]; then b_char="█"; else b_char=" "; fi
        
        printf "%*s │ %s │   │ %s │\n" $((COLS/2 - 7)) "" "$v_char" "$b_char"
    done

    # Bottom Border (Tutup Bawah)
    printf "%*s ├───┤   ├───┤\n" $((COLS/2 - 7)) ""
    printf "%*s │%02d │   │%02d │\n" $((COLS/2 - 7)) "" "$VOL" "$BRIGHT"
    printf "%*s └───┘   └───┘\n" $((COLS/2 - 7)) ""
    printf "%*s <Vol>   <Bri>\n" $((COLS/2 - 7)) ""
    
    echo ""
    center "W/S: Volume | I/K: Brightness | Q: Quit"

    # Kontrol Input
    read -rsn1 key
    case $key in
        w|W) amixer sset Master 5%+ > /dev/null ;;
        s|S) amixer sset Master 5%- > /dev/null ;;
        i|I) brightnessctl set +5% > /dev/null ;;
        k|K) brightnessctl set 5%- > /dev/null ;;
        q|Q) break ;;
    esac
done
