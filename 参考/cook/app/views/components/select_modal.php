<!-- 通用选择模态框 -->
<div id="selectModal" class="selectModal-overlay" style="display:none;" onclick="overlayClick(event)">
    <div class="selectModal-box">
        <h3 id="selectTitle"></h3>
        <div id="selectContent" class="selectModal-content"></div>
        <div class="selectModal-actions">
            <button id="selectCloseBtn" class="btn-cancel" onclick="closeModal()">关闭</button>
        </div>
    </div>
</div>
<script src="assets/js/select_modal.js"></script>