CREATE TABLE IF NOT EXISTS extraction_configs (
    config_id text PRIMARY KEY,
    parameters jsonb NOT NULL,
    dimensions jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS images (
    image_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    relative_path text NOT NULL UNIQUE,
    sha256 text NOT NULL CHECK (length(sha256) = 64),
    pixel_sha256 text NOT NULL CHECK (length(pixel_sha256) = 64),
    width integer NOT NULL CHECK (width > 0),
    height integer NOT NULL CHECK (height > 0),
    species_code integer,
    species_name text,
    source_image_id text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS images_species_idx ON images(species_code);
CREATE INDEX IF NOT EXISTS images_pixel_hash_idx ON images(pixel_sha256);

CREATE TABLE IF NOT EXISTS image_features (
    image_id bigint NOT NULL REFERENCES images(image_id) ON DELETE CASCADE,
    config_id text NOT NULL REFERENCES extraction_configs(config_id),
    source_sha256 text NOT NULL,
    glcm double precision[] NOT NULL,
    ulbp double precision[] NOT NULL,
    geometry double precision[] NOT NULL,
    contour_profile double precision[] NOT NULL,
    fourier double precision[] NOT NULL,
    hsv double precision[] NOT NULL,
    color_moments double precision[] NOT NULL,
    spatial_hsv double precision[] NOT NULL,
    metadata jsonb NOT NULL,
    extracted_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (image_id, config_id)
);

-- PostgreSQL khong tu rang buoc so chieu trong khai bao float8[n].
-- Trigger kiem tra theo cau hinh, ca khi INSERT truc tiep bang SQL.
CREATE OR REPLACE FUNCTION validate_feature_dimensions() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE dims jsonb; field text; vec double precision[];
BEGIN
    SELECT dimensions INTO STRICT dims FROM extraction_configs WHERE config_id=NEW.config_id;
    FOREACH field IN ARRAY ARRAY['glcm','ulbp','geometry','contour_profile','fourier','hsv','color_moments','spatial_hsv'] LOOP
        EXECUTE format('SELECT ($1).%I', field) INTO vec USING NEW;
        IF array_ndims(vec) IS DISTINCT FROM 1
           OR cardinality(vec) <> (dims->>field)::integer
           OR array_lower(vec,1) <> 1
           OR EXISTS (SELECT 1 FROM unnest(vec) v WHERE v IS NULL OR v IN ('NaN'::float8,'Infinity'::float8,'-Infinity'::float8)) THEN
            RAISE EXCEPTION 'Invalid vector: %', field;
        END IF;
    END LOOP;
    RETURN NEW;
END;
$$;
CREATE OR REPLACE TRIGGER feature_dimensions BEFORE INSERT OR UPDATE ON image_features
FOR EACH ROW EXECUTE FUNCTION validate_feature_dimensions();

CREATE OR REPLACE VIEW feature_catalog AS
SELECT i.image_id, i.relative_path, i.species_code, i.species_name,
       f.config_id, f.geometry[1] AS aspect_ratio, f.geometry[2] AS solidity,
       f.geometry[3] AS extent, f.metadata, f.extracted_at
FROM images i JOIN image_features f USING(image_id)
WHERE f.source_sha256 = i.sha256;
