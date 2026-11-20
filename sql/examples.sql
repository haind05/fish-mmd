-- Thong ke so anh, so loai (nhan tu ten file, chua kiem chung sinh hoc).
SELECT count(*) AS images, count(DISTINCT species_code) AS species FROM images;
SELECT config_id, count(*) AS feature_sets FROM feature_catalog GROUP BY config_id;
SELECT relative_path, aspect_ratio, solidity, extent
FROM feature_catalog ORDER BY relative_path LIMIT 10;

-- Xem vector va do dai.
SELECT i.relative_path, f.glcm, cardinality(f.ulbp) AS ulbp_dimensions,
       cardinality(f.spatial_hsv) AS spatial_dimensions
FROM images i JOIN image_features f USING(image_id) LIMIT 1;

-- Anh can xem lai mat na.
SELECT relative_path, metadata->'warnings' AS warnings FROM feature_catalog
WHERE jsonb_array_length(metadata->'warnings') > 0;

-- Kiem tra trung pixel, khong chi trung file nhi phan.
SELECT pixel_sha256, count(*) FROM images GROUP BY pixel_sha256 HAVING count(*) > 1;

-- Xoa mot anh (thay duong dan): dac trung tu dong xoa theo ON DELETE CASCADE.
-- DELETE FROM images WHERE relative_path='species_...png';
