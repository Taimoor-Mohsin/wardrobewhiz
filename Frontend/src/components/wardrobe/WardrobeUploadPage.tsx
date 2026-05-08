import { useState, useCallback } from "react";
import { ImageUploadZone } from "./ImageUploadZone";
import { ImagePreviewGrid } from "./ImagePreviewGrid";
import { MetadataForm } from "./MetadataForm";
import { WardrobeItemForm } from "./WardrobeItemForm";
import { UploadProgress } from "./UploadProgress";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Upload } from "lucide-react";
import { createImagePreview, validateImageFile, compressImage } from "@/lib/utils/imageUtils";
import { uploadApi } from "@/lib/api/upload";
import type { UploadedImage, WardrobeItem, WardrobeItemMetadata, GarmentCategory, GarmentType, Season } from "@/types/wardrobe";
import type { UploadStatus } from "./UploadProgress";
import { useQueryClient } from "@tanstack/react-query";

interface WardrobeUploadPageProps {
  onUploadComplete?: (items: WardrobeItem[]) => void;
  maxFiles?: number;
}

export const WardrobeUploadPage = ({
  onUploadComplete,
  maxFiles = 20,
}: WardrobeUploadPageProps) => {
  const queryClient = useQueryClient();
  const [uploadedImages, setUploadedImages] = useState<UploadedImage[]>([]);
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadMessage, setUploadMessage] = useState<string>("");
  const [reviewItems, setReviewItems] = useState<WardrobeItem[]>([]);
  const [reviewIndex, setReviewIndex] = useState(0);

  const activeReviewItem = reviewItems[reviewIndex];

  const finalizeUploadFlow = useCallback((items: WardrobeItem[]) => {
    setUploadedImages([]);
    setSelectedImageId(null);
    setReviewItems([]);
    setReviewIndex(0);
    setUploadStatus("idle");
    setUploadProgress(0);

    if (onUploadComplete) {
      onUploadComplete(items);
    }
  }, [onUploadComplete]);

  const handleFilesSelected = useCallback(async (files: File[]) => {
    console.log("[WardrobeUpload] Files selected", {
      count: files.length,
      files: files.map((file) => ({
        name: file.name,
        type: file.type,
        size: file.size,
      })),
    });

    const validFiles: File[] = [];
    const errors: string[] = [];

    // Validate files
    for (const file of files) {
      const validation = validateImageFile(file);
      if (validation.valid) {
        validFiles.push(file);
      } else {
        errors.push(`${file.name}: ${validation.error}`);
      }
    }

    if (errors.length > 0) {
      console.warn("Some files were rejected:", errors);
    }

    // Create previews and metadata
    const newImages: UploadedImage[] = await Promise.all(
      validFiles.map(async (file) => {
        const preview = await createImagePreview(file);
        const id = `${Date.now()}-${Math.random()}`;
        return {
          id,
          file,
          preview,
          metadata: {
            category: "Tops" as GarmentCategory,
            type: "Shirt" as GarmentType,
            color: "#000000",
            season: "All-Season" as Season,
          },
        };
      })
    );

    console.log("[WardrobeUpload] Prepared preview entries", {
      validCount: newImages.length,
      maxFiles,
    });

    setUploadedImages((prev) => [...prev, ...newImages].slice(0, maxFiles));
  }, [maxFiles]);

  const handleRemoveImage = useCallback((id: string) => {
    setUploadedImages((prev) => prev.filter((img) => img.id !== id));
    if (selectedImageId === id) {
      setSelectedImageId(null);
    }
  }, [selectedImageId]);

  const handleMetadataChange = useCallback((metadata: WardrobeItemMetadata) => {
    if (!selectedImageId) return;

    setUploadedImages((prev) =>
      prev.map((img) =>
        img.id === selectedImageId ? { ...img, metadata } : img
      )
    );
  }, [selectedImageId]);

  const handleReviewDialogChange = useCallback((open: boolean) => {
    if (!open && reviewItems.length > 0) {
      finalizeUploadFlow(reviewItems);
    }
  }, [finalizeUploadFlow, reviewItems]);

  const handleUpload = useCallback(async () => {
    console.log("[WardrobeUpload] Upload button clicked", {
      imageCount: uploadedImages.length,
      selectedImageId,
    });

    if (uploadedImages.length === 0) {
      console.warn("[WardrobeUpload] Upload aborted: no images selected");
      return;
    }

    setUploadStatus("uploading");
    setUploadProgress(0);
    setUploadMessage("Compressing images...");

    try {
      // Compress images
      const compressedFiles = await Promise.all(
        uploadedImages.map((img) => compressImage(img.file))
      );

      console.log("[WardrobeUpload] Compression complete", {
        originalCount: uploadedImages.length,
        compressedCount: compressedFiles.length,
        files: compressedFiles.map((file) => ({
          name: file.name,
          size: file.size,
          type: file.type,
        })),
      });

      setUploadMessage("Uploading to server...");

      // Simulate upload progress (replace with actual API call)
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      console.log("[WardrobeUpload] Starting API request", {
        endpoint: "/api/upload/batch",
        metadataCount: uploadedImages.length,
      });

      const response = await uploadApi.uploadBatch(
        compressedFiles,
        uploadedImages.map((img) => img.metadata!),
        (progress) => setUploadProgress(progress.percentage)
      );

      console.log("[WardrobeUpload] API request succeeded", {
        itemCount: response.items.length,
        errorCount: response.errors?.length ?? 0,
        errors: response.errors ?? [],
      });

      if (response.items.length === 0 && response.errors && response.errors.length > 0) {
        throw new Error(response.errors.join(", "));
      }

      clearInterval(progressInterval);
      setUploadProgress(100);
      setUploadStatus("success");
      setUploadMessage(`${response.items.length} items uploaded successfully!`);
      await queryClient.invalidateQueries({ queryKey: ["wardrobe"] });
      await queryClient.invalidateQueries({ queryKey: ["wardrobe", "stats"] });

      if (response.items.length > 0) {
        console.log("[WardrobeUpload] Uploaded item received", response.items[0]);
        setReviewItems(response.items);
        setReviewIndex(0);
        return;
      }

      finalizeUploadFlow(response.items);
    } catch (error) {
      setUploadStatus("error");
      setUploadMessage("Upload failed. Please try again.");
      console.error("[WardrobeUpload] Upload failed", error);
    }
  }, [finalizeUploadFlow, queryClient, selectedImageId, uploadedImages]);

  const selectedImage = uploadedImages.find((img) => img.id === selectedImageId);
  const canUpload = uploadedImages.length > 0 && uploadedImages.every((img) => img.metadata);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Upload Wardrobe Items</h1>
        <p className="text-muted-foreground mt-2">
          Upload photos of your garments to build your digital wardrobe
        </p>
      </div>

      <Tabs defaultValue="upload" className="w-full">
        <TabsList>
          <TabsTrigger value="upload">Upload Images</TabsTrigger>
          <TabsTrigger value="preview" disabled={uploadedImages.length === 0}>
            Preview ({uploadedImages.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upload" className="space-y-6">
          <ImageUploadZone
            onFilesSelected={handleFilesSelected}
            maxFiles={maxFiles}
            disabled={uploadStatus === "uploading"}
          />

          {uploadedImages.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Uploaded Images</CardTitle>
                <CardDescription>
                  {uploadedImages.length} image{uploadedImages.length !== 1 ? "s" : ""} ready
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ImagePreviewGrid
                  images={uploadedImages}
                  onRemove={handleRemoveImage}
                  onEdit={setSelectedImageId}
                />
              </CardContent>
            </Card>
          )}

          {selectedImage && (
            <MetadataForm
              metadata={selectedImage.metadata!}
              onChange={handleMetadataChange}
            />
          )}

          {uploadedImages.length > 0 && !selectedImage && (
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground text-center">
                  Click "Edit Metadata" on any image to add details, or upload all items with default metadata.
                </p>
              </CardContent>
            </Card>
          )}

          <div className="flex justify-end gap-4">
            <Button
              variant="outline"
              onClick={() => {
                setUploadedImages([]);
                setSelectedImageId(null);
              }}
              disabled={uploadedImages.length === 0 || uploadStatus === "uploading"}
            >
              Clear All
            </Button>
            <Button
              onClick={handleUpload}
              disabled={!canUpload || uploadStatus === "uploading"}
            >
              {uploadStatus === "uploading" ? (
                <>
                  <Upload className="mr-2 h-4 w-4 animate-pulse" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload {uploadedImages.length} Item{uploadedImages.length !== 1 ? "s" : ""}
                </>
              )}
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="preview" className="space-y-6">
          <ImagePreviewGrid
            images={uploadedImages}
            onRemove={handleRemoveImage}
            onEdit={setSelectedImageId}
          />
        </TabsContent>
      </Tabs>

      <UploadProgress
        progress={uploadProgress}
        status={uploadStatus}
        message={uploadMessage}
      />

      <Dialog open={reviewItems.length > 0} onOpenChange={handleReviewDialogChange}>
        <DialogContent className="max-w-5xl">
          <DialogHeader>
            <DialogTitle>Review Uploaded Item</DialogTitle>
            <DialogDescription>
              Confirm or correct the AI-generated metadata before continuing.
              {reviewItems.length > 1 ? ` Item ${reviewIndex + 1} of ${reviewItems.length}.` : ""}
            </DialogDescription>
          </DialogHeader>

          {activeReviewItem && (
            <WardrobeItemForm
              item={activeReviewItem}
              flowLabel="upload-review"
              cancelLabel="Review Later"
              saveLabel={reviewIndex < reviewItems.length - 1 ? "Save & Next" : "Save & Finish"}
              previewDetails={(
                <>
                  <p className="text-xs text-muted-foreground">
                    Current AI color: {activeReviewItem.colorLabel || activeReviewItem.color}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Current AI season: {activeReviewItem.season}
                  </p>
                </>
              )}
              onCancel={() => finalizeUploadFlow(reviewItems)}
              onUpdated={(updatedItem) => {
                console.log("[WardrobeUpload] Updated item returned", updatedItem);

                const nextReviewItems = reviewItems.map((item, index) =>
                  index === reviewIndex ? updatedItem : item
                );

                setReviewItems(nextReviewItems);

                if (reviewIndex >= nextReviewItems.length - 1) {
                  finalizeUploadFlow(nextReviewItems);
                  return;
                }

                setReviewIndex((prev) => prev + 1);
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

