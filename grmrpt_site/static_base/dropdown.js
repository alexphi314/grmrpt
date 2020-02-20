$(document).ready(function(){
	$(".dropdown").hover(function(){
		var dropdownMenu = $(this).children("#dropdownMenuButton");
		if(dropdownMenu.is(":visible")){
			dropdownMenu.parent().toggleClass("open");
		}
	});
});