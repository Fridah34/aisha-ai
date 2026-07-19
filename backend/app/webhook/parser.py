def extract_message_data(form: dict) -> dict | None:
    """
    Pulls the fields we need from Twilio's webhook form payload.

    Twilio sends form-encoded data (not JSON) with these fields:
        From        = "whatsapp:+254712345678"
        To          = "whatsapp:+14155238886"
        Body        = "Habari, mna sneakers?"
        ProfileName = "John"
        NumMedia    = "0"
        
    Interactive taps come back differently depending on which Content
    template produced them - confirmed against real webhook payloads,
    not assumed:
    
    twilio/list-picker (our category/store menus) sends:
        ListId = "opt_1"    #the `id` defined at template creation
        ListTitle = "Dress" # the visible label the customer tapped
        Body = "opt_1"      # NOT the label - this is the id, unhelpfully
        
    For a tapped List Picker item or Quick Reply button, Twilio instead
    (or additionally) sends:
        ButtonPayload = "opt_1"  #the `id` you defined at template creation
        ButtonText = "Dress"     #the visible label the customer tapped
        ButtonType = "REPLY"     # REPLY (quick-reply/list) or ACTION
        
    Body is often empty or missing on these - ButtonPayload is what identifies the actual
    selection, so it's checked before falling back to Body.
    

    Returns a flat dict the router needs, or None if we should ignore
    the event (status callbacks, media-only messages, missing fields).
    """
    # Ignore Twilio status callbacks — they have MessageStatus but no Body
    if "MessageStatus" in form and "Body" not in form:
        return None

    try:
        from_raw = form.get("From", "")
        to_raw   = form.get("To", "")
        body     = form.get("Body", "").strip()
        
        # List Picker reply (category/store menu taps)
        list_id = form.get("ListId", "").strip()
        list_title = form.get("ListTitle", "").strip()
        
        #Quick Reply reply (checkout / add more/ browse more taps)
        button_payload = form.get("ButtonPayload", "").strip()
        button_text = form.get("ButtonText", "").strip()

        #Whichever ineractive type this is, normalize to one shape -
        #router.py/marketplace_flow.py only need "what was tapped",
        #not which Twilio content type produced it.
        interactive_id = list_id or button_payload
        interactive_label = list_title or button_text
        
        
        if not from_raw or not to_raw:
            return None

        # Strip "whatsapp:" prefix to get plain phone numbers
        phone_number  = from_raw.replace("whatsapp:", "").strip()
        twilio_number = to_raw.replace("whatsapp:", "").strip()

        num_media = int(form.get("NumMedia", "0") or "0")
        
        # --Interactive reply (list picker item or quick-reply button tapped) --
        #Checked before the plain-text/media branches since Body is 
        #unreliiable on these (empty for quick-reply, or holding the raw
        # id instead of the label for list-picker) - interactive_id is
        #tap is the real signal, not typed text.
        if interactive_id:
            return{
                "phone_number": phone_number,
                "message_text": interactive_label or interactive_id ,
                "button_payload": interactive_id,
                "twilio_number": twilio_number,
                "customer_name": form.get("ProfileName"),
                "message_type": "interactive",
            }

        # Media message (image, voice note, sticker) with no text
        if num_media > 0 and not body:
            return {
                "phone_number":  phone_number,
                "message_text":  None,
                "twilio_number": twilio_number,
                "customer_name": form.get("ProfileName"),
                "message_type":  "media",
            }

        # Empty body with no media — unknown event, ignore
        if not body:
            return None

        return {
            "phone_number":  phone_number,
            "message_text":  body,
            "twilio_number": twilio_number,
            "customer_name": form.get("ProfileName"),
            "message_type":  "text",
        }

    except (KeyError, ValueError, TypeError) as e:
        print(f"[Parser] Failed to parse Twilio payload: {e}")
        return None