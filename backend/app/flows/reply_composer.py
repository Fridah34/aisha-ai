import random

# ---------------------------------------------------------------------------
# Reply composer — separates FACTS (always built from real data, never
# varied) from PRESENTATION (small phrase fragments, recombined for
# variety). Adding a new reply state means composing existing fragments,
# not writing new full sentences by hand.
#
# NOTE: this file holds NO product/variant data of any kind (no colors,
# sizes, etc.) — those always come from the DB via marketplace_flow.py and
# are passed in through `facts`. This file only owns wrapper phrasing.
# ---------------------------------------------------------------------------

OPENERS = {
    "product_pick": ["Great choice!", "Nice pick!", "Good choice!"],
    "confirm_add": ["Added", "Got it —", "🛒 Added"],
    "apology": ["Sorry,", "Hmm,", "Sorry —"],
    "invalid_size": [
        "Please choose one of:",
        "That's not quite it — please choose one of:",
        "Please pick one of:",
    ],
    "no_photo": ["Sorry,", "Ah,", "Sorry —"],
    "empty_cart": [
        "Your cart is empty.",
        "Looks like your cart's empty.",
        "Your cart is empty right now.",
    ],
    "ask_checkout_info": ["Almost there!", "Just about done!", "One more step!"],
    "order_confirmed": [
        "Your order has been placed ✅",
        "Order confirmed ✅",
        "You're all set — order placed ✅",
    ],
    "store_gone": [
        "That store isn't available anymore.",
        "Hmm, that store isn't available right now.",
        "That store's no longer active.",
    ],
    # CHANGED: new opener for the "customer named a variant we don't stock
    # on this product" case — deliberately separate from "apology" so this
    # state can be retuned independently later without affecting other
    # apology-shaped replies.
    "unavailable_variant": ["Looks like", "Ah,", "Hmm,"],
}

CLOSERS = {
    "ask_quantity": [
        "Reply with a valid quantity number to choose how many you want.",
        "Just let me know the quantity!",
        "How many should I add?",
    ],
    "ask_size": [
        "Which one would you like?",
        "Which option works for you?",
    ],
    "post_add": [
        "Reply 'checkout' to complete your order, or send another product to add more.",
        "Ready to checkout, or want to keep shopping?",
    ],
    "no_match": [
        "Reply with a product name from the list above, or 'menu' to start over.",
        "Try a product name from the list above, or 'menu' to see everything again.",
    ],
    "cart_no_match": [
        "Reply 'checkout' to complete your order, or send a product name to add more.",
        "Not sure I follow — reply 'checkout' when ready, or name another product to keep shopping.",
    ],
    "browse_menu": [
        "Reply 'menu' to browse and find something you like!",
        "Let's find you something — reply 'menu' to browse.",
        "Reply 'menu' whenever you're ready to browse.",
    ],
    # CHANGED: closer for the unavailable-variant case — separate from
    # "no_match" because this is a soft nudge toward what IS available,
    # not a "you did something wrong" message.
    "explore_alternatives": [
        "Would you like to pick from those instead?",
        "Want to check out what we do have?",
        "Would you like to explore the options available?",
    ],
}


def compose(
    *, opener_key: str | None, closer_key: str | None = None, facts: str = ""
) -> str:
    """facts is a pre-built, already-correct string (price/product/qty/
    variant options formatted from real DB data before this is called) —
    composition only varies the wrapper text around it, never touches the
    facts, and never contains any product/variant data of its own.

    Shapes supported:
    - opener_key=None, closer_key set, facts="" : legacy single-line
      apology+closer (awaiting_product_choice / awaiting_cart_action
      no-match). Kept as its own branch so the four states already in
      production don't change output shape.
    - opener_key set, closer_key set            : "{opener} {facts}\n\n{closer}"
      (or "{opener}\n\n{closer}" if facts is empty) — product_pick /
      confirm_add / unavailable_variant.
    - closer_key=None                            : single-line
      "{opener} {facts}" — used by short one-shot replies (invalid
      size choice, no-photo-available) that don't need a follow-up
      prompt of their own.
    """
    opener = (
        random.choice(OPENERS["apology"])
        if opener_key is None
        else random.choice(OPENERS[opener_key])
    )
    closer = random.choice(CLOSERS[closer_key]) if closer_key else None

    # Legacy shape — preserves exact output of the four states already wired.
    if opener_key is None and closer_key:
        return f"{opener} {closer}"

    body = f"{opener} {facts}" if facts else opener
    return f"{body}\n\n{closer}" if closer else body
