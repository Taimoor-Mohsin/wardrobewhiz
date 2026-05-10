from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


USER_PROFILE_COLUMNS = {
    "usual_contexts_json": "TEXT",
    "usual_context_other": "TEXT",
    "style_text": "TEXT",
    "formality_level": "INTEGER",
    "comfort_style_level": "INTEGER",
    "modesty_preference": "VARCHAR",
    "preferred_styles_json": "TEXT",
    "preferred_colors_json": "TEXT",
    "disliked_colors_json": "TEXT",
    "preferred_occasions_json": "TEXT",
    "eastern_western_preference": "VARCHAR",
    "clothing_avoid_text": "TEXT",
    "fit_preference": "VARCHAR",
    "layering_preference": "VARCHAR",
    "accessories_preference": "VARCHAR",
    "height": "VARCHAR",
    "weight": "VARCHAR",
    "collar": "VARCHAR",
    "waist": "VARCHAR",
    "inseam": "VARCHAR",
    "shoe_size": "VARCHAR",
    "chest": "VARCHAR",
    "shoulder": "VARCHAR",
    "sleeve_length": "VARCHAR",
    "profile_completed": "BOOLEAN NOT NULL DEFAULT 0",
    "completed_at": "DATETIME",
    "style_vector_json": "TEXT",
    "created_at": "DATETIME",
    "updated_at": "DATETIME",
}

WARDROBE_ITEM_COLUMNS = {
    "name": "VARCHAR",
    "segmented_image_path": "VARCHAR",
    "color": "VARCHAR",
    "season": "VARCHAR",
    "description": "TEXT",
    "wear_count": "INTEGER NOT NULL DEFAULT 0",
    "last_worn": "DATETIME",
}


def add_missing_columns(engine: Engine, table_name: str, columns: dict[str, str]) -> None:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}

    with engine.begin() as connection:
        for column_name, column_type in columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                )


def apply_sqlite_dev_migrations(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    add_missing_columns(engine, "user_profiles", USER_PROFILE_COLUMNS)
    add_missing_columns(engine, "wardrobe_items", WARDROBE_ITEM_COLUMNS)
