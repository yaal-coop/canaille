$(function(){
    $(".photo-delete-icon").click(function(event){
        event.preventDefault();
        $(".photo-content").hide();
        $(".photo-placeholder").show();
        $(".photo-field").val("");
        $(".photo-delete-button").prop("checked", true);
    });

    $(".photo-field").change(function(event){
        var upload = URL.createObjectURL(event.target.files[0]);
        $(".photo-content").show();
        $(".photo-placeholder").hide();
        $(".photo-content img").attr("src", upload);
        $(".photo-delete-button").prop("checked", false);
    });
});
