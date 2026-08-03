 <!-- 主菜单页面 -->
 <div id="menuPage" class="content-page active">
     <div class="list-menu">
         <div class="menu-item" onclick="goToPage('favorites')">
             <div class="menu-item-title">❤️ 我的收藏</div>
         </div>
         <div class="menu-item" onclick="goToPage('history')">
             <div class="menu-item-title">🕒 浏览历史</div>
         </div>
         <div class="menu-item" onclick="goToPage('recipes')">
             <div class="menu-item-title">📖 我的菜谱</div>
         </div>
         <div class="menu-item" onclick="goToPage('ingredients')">
             <div class="menu-item-title">🥘 食材管理</div>
         </div>
         <div class="menu-item" onclick="goToPage('seasonings')">
             <div class="menu-item-title">🧂 调味品管理</div>
         </div>
         <div class="menu-item" onclick="goToPage('deletedRecipes')">
             <div class="menu-item-title">🗑️ 回收站</div>
         </div>
         <div class="menu-item" onclick="goToPage('categories')">
             <div class="menu-item-title">📁 菜谱分类管理</div>
         </div>

         <div class="menu-item" onclick="goToPage('ing-categories')">
             <div class="menu-item-title">🏷️ 食材分类管理</div>
         </div>

         <div class="menu-item" onclick="goToPage('seasoning-categories')">
             <div class="menu-item-title">🏷️ 调味品分类管理</div>
         </div>

     </div>

     <div class="list-menu">
         <div class="menu-item" onclick="goToPage('settings')">
             <div class="menu-item-title">⚙️ 设置</div>
         </div>
         <div class="menu-item" onclick="window.location.href='/zb_system/admin/index.php?act=admin'">
             <div class="menu-item-title">ℹ️ 后台首页</div>
         </div>


     </div>

     <div class="button-group">
         <button class="btn-action btn-cancel" onclick="logout()">退出登录</button>

     </div>
 </div>