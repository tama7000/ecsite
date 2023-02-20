from django.shortcuts import render 
from django.shortcuts import render, redirect  # 追加
from django.contrib.auth import authenticate, login  # 追加
from .forms import CustomUserCreationForm  # 追加
from django.shortcuts import get_object_or_404, render, redirect  # 追加
from .models import Product # 追加
from django.contrib.auth.decorators import login_required  # 追加
from django.views.decorators.http import require_POST  # 追加
from django.contrib import messages # 追加
from .forms import AddToCartForm # 追加
from .models import Sale  # 追加
from .forms import PurchaseForm  # 追加

import json  # 追加

import sys
sys.path.append('\users\yu-mizuno\desktop\log_\log3\ecsite\myvenv\lib\site-packages')

import requests  # 追加 
@login_required
@require_POST
def toggle_fav_product_status(request): 
  """お気に⼊り状態を切り替える関数""" 
 
  product = get_object_or_404(Product, pk=request.POST["product_id"]) 
  user = request.user 
 
  if product in user.fav_products.all(): 
    # productがユーザーのfav_productsに既に存在している場合(お気に⼊り済の場合) 
    # → productをfav_productsから除外する(お気に⼊りを外す) 
    user.fav_products.remove(product) 
  else: 
    # productがユーザーのfav_productsに存在しない場合(お気に⼊りしていない場合) 
    # → productをfav_productsに追加する(お気に⼊り登録する) 
    user.fav_products.add(product) 
  return redirect('app:detail', product_id=product.id) 

def index(request): 
  return render(request, 'app/index.html') 

def signup(request): 




  if request.method == 'POST': 
    form = CustomUserCreationForm(request.POST) 
    if form.is_valid(): 
      form.save() 
      input_email = form.cleaned_data['email'] 
      input_password = form.cleaned_data['password1'] 
      new_user = authenticate( 
        email=input_email, 
        password=input_password, 
      ) 
      if new_user is not None: 
        login(request, new_user) 
        return redirect('app:index') 
  else: 
    form = CustomUserCreationForm() 
  return render(request, 'app/signup.html', {'form': form}) 

def detail(request, product_id): 
  product = get_object_or_404(Product, pk=product_id) 
  if request.method == "POST": 
    add_to_cart_form = AddToCartForm(request.POST) 
    if add_to_cart_form.is_valid(): 
      num = add_to_cart_form.cleaned_data['num'] 
      if 'cart' in request.session: 
        # すでに対象商品がカートにあれば新しい個数を加算、なければ新しくキーを追加する 
        if str(product_id) in request.session['cart']: 
          request.session['cart'][str(product_id)] += num 
        else: 
          request.session['cart'][str(product_id)] = num 
      else: 
        # 初めてのカート追加の場合、新しく'cart'というキーをセッションに追加する 
        request.session['cart'] = {str(product_id): num} 
      messages.success(request, f"{product.name}を{num}個カートに⼊れました!") 
      return redirect('app:detail', product_id=product_id) 
 
  # request.methodがGETのとき(画⾯にアクセスされたとき)は空のフォームを表⽰する 
  add_to_cart_form = AddToCartForm() 
  context = { 
    'product': product, 
    'add_to_cart_form': add_to_cart_form, 
  } 
  return render(request, 'app/detail.html', context)
  

def index(request): 
  products = Product.objects.all().order_by('-id') 
  print(fetch_address('1000001'))  # 追加

  return render(request, 'app/index.html', {'products': products})


@login_required
def fav_products(request): 
  user = request.user 
  products = user.fav_products.all() 
  return render(request, 'app/index.html', {'products': products}) 

@login_required
def cart(request): 
  user = request.user 




  cart = request.session.get('cart', {}) 
  cart_products = {} 
  total_price = 0 
 
  # 合計⾦額の計算 
  for product_id, num in cart.items(): 
    product = Product.objects.filter(id=product_id).first() 
    if product is None: 
      # productがNoneのとき(対象商品がデータベースから削除されている場合等)は画⾯に表⽰しない 
      continue 
    cart_products[product] = num 
    total_price += product.price * num 
 
  if request.method == 'POST': 
    purchase_form = PurchaseForm(request.POST) 
    if purchase_form.is_valid(): 
      # 住所検索ボタンが押された場合 
      if 'search_address' in request.POST: 
        zip_code = request.POST['zip_code'] 
        address = fetch_address(zip_code) 
        # 住所が取得できなかった場合はメッセージを出してリダイレクト 
        if not address: 
          messages.warning(request, "住所を取得できませんでした。") 
          return redirect('app:cart') 
        # 住所が取得できたらフォームの値として⼊⼒する 
        purchase_form = PurchaseForm( 
          initial={'zip_code': zip_code, 'address': address} 
        ) 
       
      # 購⼊処理ボタンが押された場合 
      if 'buy_product' in request.POST: 
        # 住所が⼊⼒済みかを確認する。未⼊⼒の場合はリダイレクトする。 
        if not purchase_form.cleaned_data['address']: 
          messages.warning(request, "住所の⼊⼒は必須です。") 
          return redirect('app:cart') 
        # カートが空じゃないかを確認する。空の場合はリダイレクトする。 
        if not cart: 
          messages.warning(request, "カートは空です。") 
          return redirect('app:cart') 
        # 所持ポイントが⼗分にあるかを確認する。不⾜してる場合はリダイレクトする。 
        if total_price > user.point: 
          messages.warning(request, "所持ポイントが⾜りません。") 
          return redirect('app:cart') 
 
        # 各プロダクトのSale情報を保存(売上記録の登録) 
        for product, num in cart_products.items(): 
          sale = Sale( 
            product=product, 
            user=request.user, 
            amount=num, 
            price=product.price, 
            total_price=num * product.price, 
          ) 

          sale.save() 
          user.point -= total_price 
          user.save() 
         # セッションから'cart'を削除してカートを空にする。 
        del request.session['cart'] 
        messages.success(request, "商品の購⼊が完了しました！") 
        return redirect('app:cart') 
  else: 
    purchase_form = PurchaseForm() 
  context = { 
    'purchase_form': purchase_form, 
    'cart_products': cart_products, 
    'total_price': total_price, 
  } 
  return render(request, 'app/cart.html', context)


@login_required
@require_POST
def change_product_amount(request): 
 
  # name="product_id"のフィールドの値を取得(どの商品を増減させるか) 
  product_id = request.POST["product_id"] 
  # セッションから"cart"情報を取得 
  cart_session = request.session['cart'] 
 
  # セッションの更新 
  if product_id in cart_session: 
    # 1つ減らすボタンが押された時 
    if "action_remove" in request.POST: 
      cart_session[product_id] -= 1 
    # 1つ増やすボタンが押された時 
    if "action_add" in request.POST: 

      cart_session[product_id] += 1 
    # 商品個数が0以下になった場合は、カートから対象商品を削除 
    if cart_session[product_id] <= 0: 
      del cart_session[product_id] 
  return redirect('app:cart')



def fetch_address(zip_code):

    REQUEST_URL = f'http://zipcloud.ibsnet.co.jp/api/search?zipcode={zip_code}' 
    response = requests.get(REQUEST_URL) 
    response = json.loads(response.text) 
    results, api_status = response['results'], response['status']

    address = ''
    if api_status == 200 and results is not None: 
        result = results[0] 
        address = result['address1'] + result['address2'] + result['address3'] 
    return address


# 追加
@login_required
def order_history(request): 
  user = request.user 
  sales = Sale.objects.filter(user=user).order_by('-created_at') 
  return render(request, 'app/order_history.html', {'sales': sales})