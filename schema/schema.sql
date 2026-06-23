CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

CREATE TABLE cuisines (id SERIAL PRIMARY KEY, name VARCHAR(100) UNIQUE NOT NULL, region VARCHAR(100), created_at TIMESTAMPTZ DEFAULT NOW());

CREATE TABLE diet_tags (id SERIAL PRIMARY KEY, slug VARCHAR(50) UNIQUE NOT NULL, label VARCHAR(100) NOT NULL);

CREATE TABLE meal_categories (id SERIAL PRIMARY KEY, slug VARCHAR(50) UNIQUE NOT NULL, label VARCHAR(100) NOT NULL);

CREATE TABLE difficulty_levels (id SERIAL PRIMARY KEY, slug VARCHAR(20) UNIQUE NOT NULL, label VARCHAR(50) NOT NULL, sort_order INT NOT NULL);

CREATE TABLE recipes (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), external_id VARCHAR(255), source VARCHAR(100) NOT NULL, source_url TEXT, title VARCHAR(512) NOT NULL, description TEXT, instructions TEXT, instructions_json JSONB, cuisine_id INT REFERENCES cuisines(id), category_id INT REFERENCES meal_categories(id), difficulty_id INT REFERENCES difficulty_levels(id), prep_time_minutes INT, cook_time_minutes INT, total_time_minutes INT GENERATED ALWAYS AS (COALESCE(prep_time_minutes,0) + COALESCE(cook_time_minutes,0)) STORED, servings INT, yield_description VARCHAR(255), calories NUMERIC(8,2), protein_g NUMERIC(8,2), fat_g NUMERIC(8,2), carbs_g NUMERIC(8,2), fiber_g NUMERIC(8,2), sodium_mg NUMERIC(8,2), image_url TEXT, thumbnail_url TEXT, rating NUMERIC(3,2), rating_count INT DEFAULT 0, is_verified BOOLEAN DEFAULT FALSE, title_hash CHAR(64), content_hash CHAR(64), raw_json JSONB, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());

CREATE TABLE ingredients (id SERIAL PRIMARY KEY, name VARCHAR(255) UNIQUE NOT NULL, usda_fdc_id INT, category VARCHAR(100), created_at TIMESTAMPTZ DEFAULT NOW());

CREATE TABLE recipe_ingredients (id SERIAL PRIMARY KEY, recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE, ingredient_id INT REFERENCES ingredients(id), raw_text TEXT NOT NULL, quantity NUMERIC(10,3), unit VARCHAR(50), preparation VARCHAR(255), is_optional BOOLEAN DEFAULT FALSE, sort_order INT NOT NULL DEFAULT 0);

CREATE TABLE recipe_diet_tags (recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE, tag_id INT NOT NULL REFERENCES diet_tags(id), PRIMARY KEY (recipe_id, tag_id));

CREATE TABLE recipe_search (recipe_id UUID PRIMARY KEY REFERENCES recipes(id) ON DELETE CASCADE, search_vec TSVECTOR);

CREATE TABLE import_runs (id SERIAL PRIMARY KEY, source VARCHAR(100) NOT NULL, file_path TEXT, started_at TIMESTAMPTZ DEFAULT NOW(), finished_at TIMESTAMPTZ, records_read INT DEFAULT 0, records_inserted INT DEFAULT 0, records_skipped INT DEFAULT 0, records_failed INT DEFAULT 0, error_log TEXT, status VARCHAR(20) DEFAULT 'running');

CREATE UNIQUE INDEX idx_recipes_content_hash ON recipes(content_hash) WHERE content_hash IS NOT NULL;
CREATE INDEX idx_recipes_source ON recipes(source);
CREATE INDEX idx_recipes_cuisine ON recipes(cuisine_id);
CREATE INDEX idx_recipes_total_time ON recipes(total_time_minutes);
CREATE INDEX idx_recipes_rating ON recipes(rating DESC);
CREATE INDEX idx_search_vec ON recipe_search USING GIN(search_vec);
CREATE INDEX idx_recipes_title_trgm ON recipes USING GIN(title gin_trgm_ops);

INSERT INTO difficulty_levels (slug, label, sort_order) VALUES ('easy','Easy',1),('medium','Medium',2),('hard','Hard',3);
INSERT INTO meal_categories (slug, label) VALUES ('breakfast','Breakfast'),('lunch','Lunch'),('dinner','Dinner'),('snack','Snack'),('dessert','Dessert'),('drink','Drink'),('appetizer','Appetizer'),('side','Side Dish');
INSERT INTO diet_tags (slug, label) VALUES ('vegan','Vegan'),('vegetarian','Vegetarian'),('gluten-free','Gluten-Free'),('dairy-free','Dairy-Free'),('keto','Keto'),('paleo','Paleo'),('low-carb','Low-Carb'),('nut-free','Nut-Free');
