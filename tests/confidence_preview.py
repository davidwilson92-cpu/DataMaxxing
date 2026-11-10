"""Local-only media/recovery fixture; every account, image and AI reply is synthetic."""
from campaign_controls_preview import *
os.environ['PUBLIC_BASE_URL']='http://127.0.0.1:8798'
from PIL import Image
from nova.db import SessionLocal, MediaAsset, User
from nova import storage

for _,uid,*_ in accounts:
    with SessionLocal() as db:
        db.get(User,uid).studio_intro_pending=False
        for index,name in enumerate(['Friday bouquet.jpg','Barber cancellation.jpg','Bakery collection.jpg']):
            path=storage.UPLOAD_DIR/f'{uid}-{index}.jpg'
            Image.new('RGB',(320,240),['#8849cc','#26212e','#d9ab61'][index]).save(path)
            db.add(MediaAsset(user_id=uid,filename=name,mime_type='image/jpeg',storage_key=str(path),size_bytes=path.stat().st_size))
        db.commit()

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8798,log_level='error')
