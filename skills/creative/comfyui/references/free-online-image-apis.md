# Free Online Image Generation & Stock Photo APIs

A reference of free, no-API-key-required image services that can be used when local ComfyUI/Stable Diffusion is not available or for quick testing.

## ✅ Reliable Services (Tested Working)

### 1. LoremFlickr (loremflickr.com)
**Best for: Keyword-targeted real photos**
```
https://loremflickr.com/{width}/{height}/{keyword1,keyword2}
```
- Example: `https://loremflickr.com/800/800/child,portrait,smile`
- Returns real Flickr photos matching keywords
- No API key required
- Supports multiple comma-separated keywords
- Add `?random=N` for different variations

**Pitfalls:**
- Subject matching is probabilistic, not guaranteed
- Always verify downloaded image content with vision analysis

---

## ❌ Known Problematic Services (Avoid)

### 1. Pollinations.ai (image.pollinations.ai)
**Problem:** Often returns HTML error pages instead of images
- Status: Connection reset errors common
- File size <10KB = almost certainly HTML, not image

### 2. Picsum Photos (picsum.photos)
**Problem:** No subject control - returns random photos (landscapes, still life, etc.)
- Example: `https://picsum.photos/800/800`
- Use only when you don't care about the image subject
- Do NOT use for "child photos", "portraits", or any subject-specific needs

### 3. this-person-does-not-exist.com
**Problem:** Returns 404 errors or HTML
- Status: Unreliable as of 2026

---

## 🔄 Verification Workflow (CRITICAL)

**Always verify every downloaded image:**

1. **File size check** - Reject anything < 50KB (likely HTML/error)
2. **Image validity check** - Try opening with PIL:
   ```python
   from PIL import Image
   img = Image.open(path)  # Fails if not a real image
   ```
3. **Content verification** - Use vision_analyze to confirm subject matches request:
   ```
   "Is this a [target subject]? Describe the content in detail."
   ```

**Cleanup:** Always delete invalid/incorrect image files before generating new ones.

---

## 📋 Common Keyword Examples

| Goal | Keywords |
|------|----------|
| Child portrait | `child,portrait,face,kid` |
| Happy child | `child,smile,happy,portrait` |
| Little girl | `girl,portrait,young,child` |
| Little boy | `boy,portrait,young,child` |
| Outdoor child | `child,outdoor,nature,playing` |

---

## 💡 Best Practice

1. Start with **LoremFlickr** - most reliable for keyword-targeted photos
2. Download 2-3 variations with different keyword combinations
3. Verify each with vision analysis
4. Keep the best matching one(s)
5. Clean up failed downloads
