const id = '[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}';
const path = new RegExp(`^/mobile/review/(${id})/(${id})/(${id})/?$`, 'i');
const review = path.exec(location.pathname);
if (review) {
  const [, organization, store, record] = review;
  document.querySelector('#ios-option').hidden = false;
  document.querySelector('#ios-link').href = `stabilis://review/${organization}/${store}/${record}`;
  document.querySelector('#web-link').href = `/app#labor-review/${store}/${record}`;
} else {
  document.querySelector('#link-status').textContent = 'This review link is incomplete. You can still open your workspace.';
}
