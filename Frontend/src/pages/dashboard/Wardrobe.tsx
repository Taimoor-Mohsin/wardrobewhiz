import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Upload } from "lucide-react";
import { WardrobeGrid } from "@/components/wardrobe/WardrobeGrid";
import { WardrobeFilters } from "@/components/wardrobe/WardrobeFilters";
import { useWardrobe } from "@/hooks/useWardrobe";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { WardrobeItemForm } from "@/components/wardrobe/WardrobeItemForm";
import type { WardrobeItem, WardrobeFilters as WardrobeFiltersType } from "@/types/wardrobe";

const Wardrobe = () => {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<WardrobeFiltersType>({});
  const [sortBy, setSortBy] = useState<WardrobeFiltersType["sort_by"]>("newest");
  const [editingItem, setEditingItem] = useState<WardrobeItem | null>(null);

  const { items, isLoading, deleteItem, markWorn } = useWardrobe({ ...filters, sort_by: sortBy });

  const closeEditDialog = () => {
    setEditingItem(null);
  };

  const handleEdit = (item: WardrobeItem) => {
    setEditingItem(item);
  };

  const handleDelete = (id: string) => {
    if (confirm("Are you sure you want to delete this item?")) {
      deleteItem(id);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">My Wardrobe</h1>
          <p className="text-muted-foreground mt-2">
            Manage and organize your clothing items
          </p>
        </div>
        <Button
          variant="default"
          className="shrink-0"
          onClick={() => navigate("/dashboard/wardrobe/upload")}
        >
          <Upload className="mr-2 h-4 w-4" />
          Upload Items
        </Button>
      </div>

      <WardrobeFilters filters={filters} onFiltersChange={setFilters} />

      <div className="flex justify-end">
        <Select value={sortBy} onValueChange={(v) => setSortBy(v as WardrobeFiltersType["sort_by"])}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Sort by" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="newest">Newest</SelectItem>
            <SelectItem value="most_worn">Most Worn</SelectItem>
            <SelectItem value="least_worn">Least Worn</SelectItem>
            <SelectItem value="last_worn">Last Worn</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <WardrobeGrid
        items={items}
        isLoading={isLoading}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onMarkWorn={markWorn}
      />

      <Dialog
        open={!!editingItem}
        onOpenChange={(open) => {
          if (!open) {
            closeEditDialog();
          }
        }}
      >
        <DialogContent className="max-w-5xl">
          <DialogHeader>
            <DialogTitle>Edit Item</DialogTitle>
            <DialogDescription>
              Update the metadata for this wardrobe item
              {editingItem?.subcategory ? ` (${editingItem.subcategory.replace(/-/g, " ")})` : ""}
            </DialogDescription>
          </DialogHeader>
          {editingItem && (
            <WardrobeItemForm
              item={editingItem}
              flowLabel="wardrobe-edit"
              saveLabel="Save Changes"
              onCancel={closeEditDialog}
              onUpdated={(updatedItem) => {
                console.log("[Wardrobe] Updated item returned", updatedItem);
                closeEditDialog();
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Wardrobe;
