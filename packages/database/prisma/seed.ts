import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Starting database seeding...\n');

  // 1. Create Admin User
  console.log('👤 Creating admin user...');
  const admin = await prisma.user.upsert({
    where: { email: 'admin@bibliograph.ai' },
    update: {},
    create: {
      email: 'admin@bibliograph.ai',
      username: 'admin',
      firstName: 'System',
      lastName: 'Admin',
      passwordHash: '$2b$10$YourHashedPasswordHere', // TODO: Replace with real hash
      role: 'ADMIN',
      emailVerified: true,
      isActive: true,
    },
  });
  console.log(`✅ Admin created: ${admin.email}\n`);

  // 2. Create Categories
  console.log('📚 Creating categories...');
  const categories = [
    { name: 'رمان', nameEn: 'Novel', slug: 'roman', description: 'آثار داستانی بلند' },
    { name: 'شعر', nameEn: 'Poetry', slug: 'poetry', description: 'مجموعه‌های شعری' },
    { name: 'تاریخ', nameEn: 'History', slug: 'history', description: 'کتاب‌های تاریخی' },
    { name: 'فلسفه', nameEn: 'Philosophy', slug: 'philosophy', description: 'آثار فلسفی' },
    { name: 'علمی', nameEn: 'Science', slug: 'science', description: 'کتاب‌های علمی و تخصصی' },
  ];

  const createdCategories = [];
  for (const category of categories) {
    const created = await prisma.category.upsert({
      where: { slug: category.slug },
      update: {},
      create: category,
    });
    createdCategories.push(created);
    console.log(`  ✓ ${created.name}`);
  }
  console.log(`✅ ${createdCategories.length} categories created\n`);

  // 3. Create Sample Authors
  console.log('✍️ Creating authors...');
  const authors = [
    {
      name: 'جلال آل‌احمد',
      nameEn: 'Jalal Al-e-Ahmad',
      bio: 'نویسنده و مترجم معاصر ایرانی',
      birthDate: new Date('1923-12-02'),
      deathDate: new Date('1969-09-09'),
      nationality: 'ایرانی',
    },
    {
      name: 'صادق هدایت',
      nameEn: 'Sadegh Hedayat',
      bio: 'نویسنده و مترجم پیشگام ادبیات مدرن ایران',
      birthDate: new Date('1903-02-17'),
      deathDate: new Date('1951-04-09'),
      nationality: 'ایرانی',
    },
    {
      name: 'فریدون م. توللی',
      nameEn: 'Freydoon Tavallali',
      bio: 'شاعر و نویسنده معاصر',
      birthDate: new Date('1940-01-01'),
      nationality: 'ایرانی',
    },
  ];

  const createdAuthors = [];
  for (const author of authors) {
    const created = await prisma.author.create({
      data: author,
    });
    createdAuthors.push(created);
    console.log(`  ✓ ${created.name}`);
  }
  console.log(`✅ ${createdAuthors.length} authors created\n`);

  // 4. Create Sample Translators
  console.log('🌐 Creating translators...');
  const translators = [
    {
      name: 'احمد کریمی حکاک',
      nameEn: 'Ahmad Karimi Hakkak',
      bio: 'مترجم و محقق برجسته ایرانی',
      nationality: 'ایرانی',
    },
    {
      name: 'نجف دریابندری',
      nameEn: 'Najaf Daryabandari',
      bio: 'از بزرگترین مترجمان ادبیات انگلیسی به فارسی',
      birthDate: new Date('1929-03-05'),
      nationality: 'ایرانی',
    },
  ];

  const createdTranslators = [];
  for (const translator of translators) {
    const created = await prisma.translator.create({
      data: translator,
    });
    createdTranslators.push(created);
    console.log(`  ✓ ${created.name}`);
  }
  console.log(`✅ ${createdTranslators.length} translators created\n`);

  // 5. Create Sample Books
 // 5. Create Sample Books (use upsert so seed is idempotent)
console.log('📖 Creating books...');

const book1 = await prisma.book.upsert({
  where: { isbn: '978-600-123-456-7' },
  update: {
    title: 'بوف کور',
    titleEn: 'The Blind Owl',
    publicationYear: 1937,
    publisher: 'امیرکبیر',
    language: 'fa',
    pageCount: 180,
    description: 'یکی از مهم‌ترین آثار ادبیات معاصر ایران',
    status: 'PUBLISHED',
    authorId: createdAuthors[1].id, // Sadegh Hedayat
  },
  create: {
    title: 'بوف کور',
    titleEn: 'The Blind Owl',
    isbn: '978-600-123-456-7',
    publicationYear: 1937,
    publisher: 'امیرکبیر',
    language: 'fa',
    pageCount: 180,
    description: 'یکی از مهم‌ترین آثار ادبیات معاصر ایران',
    status: 'PUBLISHED',
    authorId: createdAuthors[1].id, // Sadegh Hedayat
  },
});

const book2 = await prisma.book.upsert({
  where: { isbn: '978-600-123-456-8' },
  update: {
    title: 'غربزدگی',
    titleEn: 'Occidentosis',
    publicationYear: 1962,
    publisher: 'رواق',
    language: 'fa',
    pageCount: 250,
    description: 'بررسی تأثیرات فرهنگ غرب بر جامعه ایرانی',
    status: 'PUBLISHED',
    authorId: createdAuthors[0].id, // Jalal Al-e-Ahmad
  },
  create: {
    title: 'غربزدگی',
    titleEn: 'Occidentosis',
    isbn: '978-600-123-456-8',
    publicationYear: 1962,
    publisher: 'رواق',
    language: 'fa',
    pageCount: 250,
    description: 'بررسی تأثیرات فرهنگ غرب بر جامعه ایرانی',
    status: 'PUBLISHED',
    authorId: createdAuthors[0].id, // Jalal Al-e-Ahmad
  },
});

console.log(`  ✓ ${book1.title}`);
console.log(`  ✓ ${book2.title}`);
console.log(`✅ Books created\n`);


  // 6. Link Books to Categories
 // 6. Link Books to Categories (idempotent)
console.log('🔗 Linking books to categories...');

const link1Exists = await prisma.bookCategory.findFirst({
  where: { bookId: book1.id, categoryId: createdCategories[0].id },
});

if (!link1Exists) {
  await prisma.bookCategory.create({
    data: {
      bookId: book1.id,
      categoryId: createdCategories[0].id,
    },
  });
  console.log(`  ✓ Linked ${book1.title} -> ${createdCategories[0].name}`);
} else {
  console.log(`  ✓ Link already exists: ${book1.title} -> ${createdCategories[0].name}`);
}

const link2Exists = await prisma.bookCategory.findFirst({
  where: { bookId: book2.id, categoryId: createdCategories[2].id },
});

if (!link2Exists) {
  await prisma.bookCategory.create({
    data: {
      bookId: book2.id,
      categoryId: createdCategories[2].id,
    },
  });
  console.log(`  ✓ Linked ${book2.title} -> ${createdCategories[2].name}`);
} else {
  console.log(`  ✓ Link already exists: ${book2.title} -> ${createdCategories[2].name}`);
}

console.log(`✅ Book-Category relations created\n`);


  // Summary
  console.log('═══════════════════════════════════════');
  console.log('🎉 Seeding completed successfully!');
  console.log('═══════════════════════════════════════');
  console.log(`📊 Summary:`);
  console.log(`   - Users: 1 (admin)`);
  console.log(`   - Categories: ${createdCategories.length}`);
  console.log(`   - Authors: ${createdAuthors.length}`);
  console.log(`   - Translators: ${createdTranslators.length}`);
  console.log(`   - Books: 2`);
  console.log(`   - Book-Category relations: 2`);
  console.log('═══════════════════════════════════════\n');
}

main()
  .catch((e) => {
    console.error('❌ Seeding failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
