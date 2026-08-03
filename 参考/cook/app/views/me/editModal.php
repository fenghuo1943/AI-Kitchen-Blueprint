<!-- 编辑模态框 -->
<div id="editModal" class="modal-overlay" style="display:none;">
    <div class="modal-box" style="max-width: 500px;">
        <h3 id="editTitle">编辑</h3>
        <input type="hidden" id="editId" autocomplete="off">
        <div class="form-group">
            <input type="text" id="editName" placeholder="名称" autocomplete="off">
        </div>
        <div class="form-group">
            <select id="editCategory" style="display:none;">
                <option value="">-选择分类-</option>
            </select>
        </div>
        <div class="modal-actions">
            <button class="btn-confirm" id="btnSaveEdit">保存</button>
            <button class="btn-cancel" id="btnCancelEdit">取消</button>
        </div>

    </div>
</div>