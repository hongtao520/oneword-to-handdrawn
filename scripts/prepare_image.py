#!/usr/bin/env python3
"""Replace only border-connected near-white pixels with the video paper color."""

from __future__ import annotations

import argparse

import cv2
import numpy as np


PAPER_BGR = (227, 241, 246)  # #F6F1E3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()

    image = cv2.imread(args.input, cv2.IMREAD_COLOR)
    if image is None:
        raise SystemExit(f"Unable to read image: {args.input}")

    near_white = np.all(image >= 245, axis=2).astype(np.uint8)
    _, labels = cv2.connectedComponents(near_white, connectivity=8)
    border_labels = np.unique(
        np.concatenate((labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]))
    )
    background_labels = border_labels[border_labels != 0]
    if len(background_labels):
        image[np.isin(labels, background_labels)] = PAPER_BGR
    if not cv2.imwrite(args.output, image):
        raise SystemExit(f"Unable to write image: {args.output}")


if __name__ == "__main__":
    main()
