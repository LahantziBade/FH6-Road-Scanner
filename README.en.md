# FH6 Road Scanner / 地平线道路扫描器

**Language / 语言 / 言語:**
[简体中文](./README.md) | English | [日本語](./README.jp.md)

A helper tool for road exploration in *Forza Horizon 6*.

It simulates row-by-row mouse movement on the map and detects whether the “Fast Travel” button in the lower-left corner disappears through screenshots, helping players locate possibly missed unexplored roads.

## Quick Start

Go to the [Releases](https://github.com/LahantziBade/FH6-Road-Scanner/releases/latest) page, download the latest version archive, unzip it, and run the program.

## Features

* Automatically scans the map row by row
* Detects possible unexplored roads
* Automatically takes screenshots, plays an alert sound, and stops when a suspected road is found
* Supports F8 hotkey to stop scanning
* Supports custom scan area, detection area, scan step size, and threshold

## How to Use

1. Open the in-game map.
2. Move the mouse onto an already explored road and confirm that the “Fast Travel” button appears in the lower-left corner.
3. Open the program and click “Capture / Update Template”.
4. Click “Test Current Difference Score” to make sure the score looks normal.
5. Click “Start Scan”, then switch back to the game and wait for the automatic scan to begin.
6. Press F8 at any time during scanning to stop.

## How It Works

This tool does not modify game files, read game memory, inject into the game process, or change save data or online data.

It only simulates mouse movement and uses screenshots to detect UI changes, essentially automating the manual “mouse-wiggling method” used to find missed roads.
