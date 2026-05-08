import apiClient from "./client";
import { normalizeWardrobeItem } from "./wardrobe";
import type { WardrobeItem } from "@/types/wardrobe";

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export const uploadApi = {
  // Upload single image with metadata
  uploadImage: async (
    file: File,
    metadata: {
      name?: string;
      category: string;
      type: string;
      color: string;
      season: string;
      notes?: string;
    },
    onProgress?: (progress: UploadProgress) => void
  ): Promise<WardrobeItem> => {
    console.log("[uploadApi] uploadImage request start", {
      endpoint: "/upload/image",
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type,
    });

    const formData = new FormData();
    console.log("[uploadApi] Appending single file to FormData", {
      fileName: file.name,
      fileType: file.type,
      fileSize: file.size,
    });
    formData.append("file", file, file.name);
    formData.append("metadata", JSON.stringify(metadata));

    try {
      const response = await apiClient.post("/upload/image", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total && onProgress) {
            onProgress({
              loaded: progressEvent.loaded,
              total: progressEvent.total,
              percentage: Math.round((progressEvent.loaded * 100) / progressEvent.total),
            });
          }
        },
      });

      console.log("[uploadApi] uploadImage request success", {
        endpoint: "/upload/image",
      });
      return normalizeWardrobeItem(response.data);
    } catch (error) {
      console.error("[uploadApi] uploadImage request failed", error);
      throw error;
    }
  },

  // Batch upload multiple images
  uploadBatch: async (
    files: File[],
    metadataArray: Array<{
      name?: string;
      category: string;
      type: string;
      color: string;
      season: string;
      notes?: string;
    }>,
    onProgress?: (progress: UploadProgress) => void
  ): Promise<{ items: WardrobeItem[]; errors?: string[] }> => {
    console.log("[uploadApi] uploadBatch request start", {
      endpoint: "/upload/batch",
      fileCount: files.length,
      files: files.map((file) => ({
        name: file.name,
        size: file.size,
        type: file.type,
      })),
    });

    const formData = new FormData();

    files.forEach((file, index) => {
      console.log("[uploadApi] Appending batch file to FormData", {
        index,
        fileName: file.name,
        fileType: file.type,
        fileSize: file.size,
      });
      formData.append("files", file, file.name);
      formData.append(`metadata_${index}`, JSON.stringify(metadataArray[index] || {}));
    });

    try {
      const response = await apiClient.post("/upload/batch", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total && onProgress) {
            onProgress({
              loaded: progressEvent.loaded,
              total: progressEvent.total,
              percentage: Math.round((progressEvent.loaded * 100) / progressEvent.total),
            });
          }
        },
      });

      console.log("[uploadApi] uploadBatch request success", {
        endpoint: "/upload/batch",
        itemCount: response.data?.items?.length ?? 0,
        errorCount: response.data?.errors?.length ?? 0,
      });
      return {
        ...response.data,
        items: (response.data?.items || []).map(normalizeWardrobeItem),
      };
    } catch (error) {
      console.error("[uploadApi] uploadBatch request failed", error);
      throw error;
    }
  },
};

