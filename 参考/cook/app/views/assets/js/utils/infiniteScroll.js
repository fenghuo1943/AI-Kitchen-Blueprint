

// infiniteScroll.js
export function setupInfiniteScroll({ containerOrId, urlBuilder, renderItem, pageSize = 10 }) {
    const container = typeof containerOrId === 'string'
        ? document.getElementById(containerOrId)
        : containerOrId;
    if (!container) {
        const name = typeof containerOrId === 'string' ? containerOrId : containerOrId?.id ?? containerOrId;
        console.warn(`setupInfiniteScroll: 容器 "${name}" 不存在`);
        return { load: () => { } };
    }

    let page = 1;
    let hasMore = true;
    let loading = false;

    function load(reset = false) {
        if (reset) {
            page = 1;
            hasMore = true;
            //container.innerHTML = '';
        }
        if (!hasMore || loading) return;
        loading = true;

        const url = urlBuilder(page, pageSize);
        apiRequest(url)
            /* fetch(url, {
                headers: {
                    'Content-Type': 'application/json'
                },
            })
                .then(r => r.json()) */
            .then(res => {
                loading = false;

                if (reset) {
                    container.innerHTML = '';
                    container.innerHTML = '';
                }
                if (res.code !== 0) {
                    if (page === 1) container.innerHTML = '<div class="empty-msg">加载失败</div>';
                    alert(res.msg || '加载失败');
                    return;
                }
                const list = res.data?.list ?? [];
                const total = res.data?.total || 0;
                if (list.length > 0) {
                    renderItem(list, container, total);
                    hasMore = page < (res.data.totalPage || 1);
                    page++;
                    if (!hasMore) {
                        showEndMessage(); // ✅ 最后一页后显示
                    }
                } else if (page === 1) {
                    container.innerHTML = '<div class="empty-msg">暂无数据</div>';
                    hasMore = false;
                } else {
                    hasMore = false;
                    hasMore = false;
                    showEndMessage(); // ✅ 防御性补充
                }
            })
            .catch(err => {
                loading = false;
                if (page === 1) container.innerHTML = '<div class="empty-msg">加载失败</div>';
                console.error(err);
            });
    }
    function showEndMessage() {
        // 防止重复添加
        if (container.querySelector('.end-msg')) return;

        const div = document.createElement('div');
        div.className = 'end-msg';
        div.textContent = '—— 到底了 ——';
        container.appendChild(div);
    }

    function onScroll() {
        if (!hasMore || loading) return;
        //const scrollBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
        const scrollBottom =
            document.documentElement.scrollHeight -
            window.innerHeight -
            window.scrollY;
        if (scrollBottom < 50) load();


    }

    window.addEventListener('wheel', onScroll);
    window.addEventListener('touchmove', onScroll);

    return { load };
}