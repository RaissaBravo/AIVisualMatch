import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CameraPhotoOutput } from "react-native-vision-camera";
import {
  DETECTION_INTERVAL_MS,
  matchRuleFor,
  SMOOTHING_WINDOW,
} from "@/src/config/recognition";
import {
  generateEmbedding,
  loadModel,
  preprocessRoi,
} from "@/src/services/embeddingService";
import { buildEmbeddingSpace } from "@/src/services/embeddingSpace";
import type { EmbeddingSpace } from "@/src/services/embeddingSpace";
import {
  averageScores,
  rankScores,
  scoreProducts,
} from "@/src/services/matchingService";
import type { ModelInfo } from "@/src/types/ModelInfo";
import type { DetectionResult, Product } from "@/src/types/Product";
import type { Rect, Size } from "@/src/utils/crop";

export function useProductRecognition(
  products: Product[],
  modelInfo: ModelInfo | null,
  output: CameraPhotoOutput,
  preview: Size,
  roi: Rect,
  enabled: boolean,
) {
  const [results, setResults] = useState<DetectionResult[]>([]);
  const [modelLoading, setModelLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const running = useRef(false);
  const space = useMemo(() => buildEmbeddingSpace(products), [products]);
  const history = useRef<{ space: EmbeddingSpace; frames: number[][] }>({
    space,
    frames: [],
  });
  const [previousSpace, setPreviousSpace] = useState(space);
  if (previousSpace !== space) {
    setPreviousSpace(space);
    setResults([]);
  }
  useEffect(() => {
    if (!modelInfo) return;
    loadModel(modelInfo)
      .then(() => setError(null))
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Falha ao carregar modelo."),
      )
      .finally(() => setModelLoading(false));
  }, [modelInfo]);
  const detect = useCallback(async () => {
    if (running.current || !modelInfo || !space.products.length || preview.width <= 0)
      return;
    running.current = true;
    setAnalyzing(true);
    try {
      const photo = await output.capturePhoto(
        { flashMode: "off", enableShutterSound: false },
        {},
      );
      try {
        const path = await photo.saveToTemporaryFileAsync();
        const rotated =
          photo.orientation === "left" || photo.orientation === "right";
        const orientedWidth = rotated ? photo.height : photo.width;
        const orientedHeight = rotated ? photo.width : photo.height;
        const tensor = await preprocessRoi(
          `file://${path}`,
          { width: orientedWidth, height: orientedHeight },
          preview,
          roi,
          modelInfo,
        );
        const embedding = await generateEmbedding(tensor, modelInfo);
        const previous =
          history.current.space === space ? history.current.frames : [];
        const frames = [
          ...previous,
          scoreProducts(embedding, space),
        ].slice(-SMOOTHING_WINDOW);
        history.current = { space, frames };
        setResults(
          rankScores(averageScores(frames), space, matchRuleFor(modelInfo.model)),
        );
        setError(null);
      } finally {
        photo.dispose();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha na inferência.");
    } finally {
      running.current = false;
      setAnalyzing(false);
    }
  }, [modelInfo, output, preview, space, roi]);
  useEffect(() => {
    if (!enabled) return;
    const initial = setTimeout(() => void detect(), 0);
    const timer = setInterval(() => void detect(), DETECTION_INTERVAL_MS);
    return () => {
      clearTimeout(initial);
      clearInterval(timer);
    };
  }, [detect, enabled]);
  return { results, modelLoading, analyzing, error };
}
