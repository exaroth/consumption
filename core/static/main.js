(function(){
	// cache
	var $window = $(window);
	var $response = $(".response-text");
	var $form = $(".req-form");
	var $req = $("input[type='text']");
	var $body = $("textarea");
	var $statusText = $(".status-text")



	$form.on("submit", function(e){
		e.preventDefault();
		$response.empty();
		$statusText.empty();

		reqType = $("input[type='radio']:checked").val()
		console.log(reqType)
		$.ajax({
			url: $req.val(),
			data: $body.val(),
			dataType: "html",
			type: reqType,
			complete: function(data, status){
				$statusText.append(data.status)
				$response.JSONView(data.responseText);

			}

		})

	})


}())
