<?php

namespace App\Repositories;

use App\Core\Database;

class RecipeSearchRepository {
    private $db;

    public function __construct() {
        $this->db = Database::getInstance();
    }

    public function search(array $params): array {
        [
            'userId' => $userId,
            'ingredients' => $ingredients,
            'category' => $category,
            'matchMode' => $matchMode,
            'keyword' => $keyword,
            'offset' => $offset,
            'pageSize' => $pageSize,
            'sort' => $sort,
            'order' => $order,
            'deleted' => $deleted
        ] = $params + [
            'ingredients' => [],
            'category' => null,
            'matchMode' => 'any',
            'keyword' => null,
            'offset' => 0,
            'pageSize' => 20,
            'sort' => 'score',
            'order' => 'desc',
            'deleted' => false
        ];

        $where = $deleted ? " WHERE r.is_deleted = 1 " : " WHERE r.is_deleted = 0 ";
        $queryParams = [];
        $scoreParams = [];

        /* =============================
           食材筛选
        ============================== */
        if (!empty($ingredients)) {
            $placeholders = implode(',', array_fill(0, count($ingredients), '?'));

            if ($matchMode === 'exact') {
                $where .= "
                AND (
                    SELECT COUNT(DISTINCT ri.ingredient_id)
                    FROM user_recipe_ingredients ri
                    WHERE ri.recipe_id = r.id
                    AND ri.ingredient_id IN ($placeholders)
                ) = " . count($ingredients);
            } else {
                $where .= "
                AND EXISTS (
                    SELECT 1
                    FROM user_recipe_ingredients ri
                    WHERE ri.recipe_id = r.id
                    AND ri.ingredient_id IN ($placeholders)
                )";
            }

            $queryParams = array_merge($queryParams, $ingredients);
        }

        /* =============================
           分类筛选
        ============================== */
        if (!empty($category)) {
            $where .= "
            AND EXISTS (
                SELECT 1
                FROM user_recipe_categories rc
                WHERE rc.recipe_id = r.id
                AND rc.category_id = ?
            )";

            $queryParams[] = $category;
        }

        /* =============================
           关键词搜索 + 评分
        ============================== */
        if (!empty($keyword)) {

            $likeKeywordFull = '%' . $keyword . '%';
            $likeKeywordPrefix = $keyword . '%';

            $where .= "
            AND (
                r.pinyin LIKE ?
                OR r.title LIKE ?
                OR r.description LIKE ?
                OR EXISTS (
                    SELECT 1
                    FROM user_recipe_categories rc
                    JOIN user_categories c ON c.id = rc.category_id
                    WHERE rc.recipe_id = r.id
                    AND c.name LIKE ?
                )
                OR EXISTS (
                    SELECT 1
                    FROM user_recipe_ingredients ri
                    JOIN user_ingredients i ON i.id = ri.ingredient_id
                    WHERE ri.recipe_id = r.id
                    AND i.name LIKE ?
                )
            )";

            $queryParams[] = $likeKeywordPrefix;
            $queryParams[] = $likeKeywordFull;
            $queryParams[] = $likeKeywordFull;
            $queryParams[] = $likeKeywordFull;
            $queryParams[] = $likeKeywordFull;

            $scoreExpr = "
                (r.title LIKE ?) * 6
                + (EXISTS (
                    SELECT 1
                    FROM user_recipe_categories rc
                    JOIN user_categories c ON c.id = rc.category_id
                    WHERE rc.recipe_id = r.id
                    AND c.name LIKE ?
                )) * 2
                + (EXISTS (
                    SELECT 1
                    FROM user_recipe_ingredients ri
                    JOIN user_ingredients i ON i.id = ri.ingredient_id
                    WHERE ri.recipe_id = r.id
                    AND i.name LIKE ?
                )) * 2
                + (r.description LIKE ?) * 2
                + (r.pinyin LIKE ?) * 1
            ";

            $scoreParams = [
                $likeKeywordFull,
                $likeKeywordFull,
                $likeKeywordFull,
                $likeKeywordFull,
                $likeKeywordPrefix
            ];
        } else {

            $scoreExpr = "0";
        }

        /* =============================
           排序
        ============================== */
        $sortMap = [
            'score'  => 'total_score',
            'date'   => 'created_at',
            'title'   => 'pinyin',
            'cook'   => 'cooked_count',
            'random' => 'RAND()'
        ];

        $sortField = $sortMap[$sort] ?? 'total_score';
        $order = strtolower($order) === 'asc' ? 'ASC' : 'DESC';
        if ($sort === 'title') {
            $order = 'ASC';
        }
        $orderBy = $sort === 'random' ? "RAND()" : "$sortField $order, created_at DESC";

        /* =============================
           总数统计
        ============================== */
        $countSql = "
            SELECT COUNT(*)
            FROM user_recipes r
            $where
        ";
        $row = $this->db->queryOne($countSql, $queryParams);
        $total = (int)array_values($row)[0];
        //$total = (int)$this->db->queryOne($countSql, $queryParams);

        /* =============================
           查询列表（核心优化：score只算一次）
        ============================== */
        $sql = "
        SELECT
            t.*,
            CAST((
                t.score
                + IFNULL(t.cooked_count,0) * 0.5
                + IF(t.is_favorited = 1,2,0)
            ) AS DECIMAL(10,2)) AS total_score
        FROM (
            SELECT
                r.id,
                r.user_id,
                r.title,
                r.pinyin,
                r.description,
                r.cook_time,
                r.created_at,
                r.deleted_at,

                IFNULL(dc.cooked_count,0) AS cooked_count,

                CAST($scoreExpr AS DECIMAL(10,2)) AS score,

                IF(fav.recipe_id IS NULL,0,1) AS is_favorited,
                IF(today.recipe_id IS NULL,0,1) AS is_in_today_menu

            FROM user_recipes r

            LEFT JOIN (
                SELECT recipe_id, COUNT(*) AS cooked_count
                FROM user_daily_recipes
                WHERE user_id = ?
                GROUP BY recipe_id
            ) dc ON r.id = dc.recipe_id

            LEFT JOIN user_favorites fav
                ON fav.recipe_id = r.id
                AND fav.user_id = ?

            LEFT JOIN user_daily_recipes today
                ON today.recipe_id = r.id
                AND today.user_id = ?
                AND today.target_date = CURDATE()

            $where

        ) t

        ORDER BY $orderBy
        LIMIT $offset,$pageSize
        ";

        $listParams = array_merge(
            [$userId, $userId, $userId],
            $queryParams,
            $scoreParams
        );

        $list = $this->db->query($sql, $listParams);

        foreach ($list as &$row) {
            $row['total_score'] = (float)$row['total_score'];
            $row['score'] = (float)$row['score'];
        }

        return [
            'list' => $list,
            'total' => $total
        ];
    }
}
