const workspaceMenu = document.querySelector('#workspace-menu');
const workspaceNavigation = document.querySelector('#workspace-navigation');

function setWorkspaceMenu(open) {
  workspaceMenu.setAttribute('aria-expanded', String(open));
  workspaceNavigation.classList.toggle('is-open', open);
}

workspaceMenu.addEventListener('click', () => {
  const open = workspaceMenu.getAttribute('aria-expanded') === 'false';
  setWorkspaceMenu(open);
  if (open) workspaceNavigation.querySelector('.side-nav a').focus();
});

workspaceNavigation.addEventListener('click', (event) => {
  const link = event.target.closest('a');
  if (!link || workspaceMenu.getAttribute('aria-expanded') !== 'true') return;
  setWorkspaceMenu(false);
  if (link.hash) document.querySelector('#workspace').focus();
});

document.addEventListener('keydown', (event) => {
  if (event.key !== 'Escape' || workspaceMenu.getAttribute('aria-expanded') !== 'true') return;
  setWorkspaceMenu(false);
  workspaceMenu.focus();
});

matchMedia('(min-width: 1121px)').addEventListener('change', () => setWorkspaceMenu(false));
