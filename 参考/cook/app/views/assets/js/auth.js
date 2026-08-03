// Tab 切换
const loginTab = document.getElementById('loginTab');
const registerTab = document.getElementById('registerTab');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');

function showLogin() {
  loginForm.classList.add('active');
  registerForm.classList.remove('active');
  loginTab.classList.add('active');
  registerTab.classList.remove('active');
}

function showRegister() {
  loginForm.classList.remove('active');
  registerForm.classList.add('active');
  loginTab.classList.remove('active');
  registerTab.classList.add('active');
}

// 初始化根据 hash
document.addEventListener('DOMContentLoaded', () => {
  if (window.location.hash === '#register') {
    showRegister();
  } else {
    showLogin();
  }
});

loginTab.addEventListener('click', showLogin);
registerTab.addEventListener('click', showRegister);

// 登录逻辑
loginForm.addEventListener('submit', async e => {
  e.preventDefault();
  const msg = document.getElementById('loginMsg');
  const btnText = document.getElementById('loginBtnText');
  const spinner = document.getElementById('loginSpinner');
  msg.textContent = '';
  btnText.textContent = '';
  spinner.style.display = 'inline-block';
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value.trim();
  if (!username || !password) {
    msg.textContent = '请输入用户名或密码';
    spinner.style.display = 'none';
    btnText.textContent = '登录';
    return;
  }
  try {
    const res = await fetch('api/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username,
        password
      })
    });
    const data = await res.json();
    spinner.style.display = 'none';
    btnText.textContent = '登录';
    if (data.code === 0) {
      localStorage.setItem('accessToken', data.data.accessToken);
      localStorage.setItem('refreshToken', data.data.refreshToken);
      msg.className = 'msg success';
      msg.textContent = '登录成功，跳转中...';
      const redirect = getRedirect();
      setTimeout(() => { window.location.href = redirect; }, 1000);
    } else {
      msg.className = 'msg error';
      msg.textContent = data.message;
    }
  } catch (err) {
    spinner.style.display = 'none';
    btnText.textContent = '登录';
    msg.className = 'msg error';
    console.error('注册失败:', err);
    msg.textContent = '网络错误，请稍后重试';
  }
});

// 注册逻辑
registerForm.addEventListener('submit', async e => {
  e.preventDefault();
  const msg = document.getElementById('registerMsg');
  const btnText = document.getElementById('regBtnText');
  const spinner = document.getElementById('regSpinner');
  msg.textContent = '';
  btnText.textContent = '';
  spinner.style.display = 'inline-block';
  const username = document.getElementById('regUsername').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value.trim();
  if (!username || !email || !password) {
    msg.textContent = '请填写完整信息';
    spinner.style.display = 'none';
    btnText.textContent = '注册';
    return;
  }
  try {
    const res = await fetch('api/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username,
        email,
        password
      })
    });
    const data = await res.json();
    spinner.style.display = 'none';
    btnText.textContent = '注册';
    if (data.code === 0) {
      msg.className = 'msg success';
      msg.textContent = '注册成功，切换到登录...';
      setTimeout(() => showLogin(), 1000);
    } else {
      msg.className = 'msg error';
      msg.textContent = data.message;
    }
  } catch (err) {
    spinner.style.display = 'none';
    btnText.textContent = '注册';
    msg.className = 'msg error';
    msg.textContent = '网络错误，请稍后重试';
  }
});
function getRedirect() {
  const params = new URLSearchParams(window.location.search);
  const url=params.get('redirect')+ window.location.hash;
  return url+ window.location.hash || '/cook/home';
}